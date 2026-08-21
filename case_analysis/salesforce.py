import asyncio
import re

import httpx

_SOQL_PATH = "/services/data/v59.0/query"

# Token budget: keep the full case payload under ~80k chars (~20k tokens) so
# it fits comfortably alongside system prompts within the gateway's context limit.
_MAX_EMAIL_BODY_CHARS = 4000   # per email — captures most content; trims quoted history
_MAX_EMAILS = 30               # most-recent N emails; ordered DESC so first = newest
_MAX_COMMENT_BODY_CHARS = 2000 # per CaseComment

# Salesforce IDs and case numbers are alphanumeric; reject anything else before
# it reaches SOQL string interpolation (SOQL has no parameterised query API here).
_SAFE_ID_RE = re.compile(r"^[A-Za-z0-9]+$")


def _soql_literal(value: str, label: str) -> str:
    if not value or not _SAFE_ID_RE.match(value):
        raise ValueError(f"Invalid {label}: {value!r}")
    return value


# Child cases subquery — ER/TIF/SRE are stored as child cases; each may also carry
# its own Jira_Key__c. RecordType.Name distinguishes Expert Request vs others.
_CHILD_CASES_SUB = (
    "(SELECT CaseNumber, Subject, RecordType.Name, Status, Jira_Key__c FROM Cases)"
)

_CASE_FIELDS = (
    "Id, CaseNumber, Subject, Status, Priority, IsEscalated, "
    "Owner.Name, CreatedDate, ClosedDate, AccountId, Account.Name, Account.Id, "
    "Account.Support_Entitlement_Type__c, Description, Has_ER__c, Jira_Key__c, "
    + _CHILD_CASES_SUB
)

CASE_SOQL = (
    f"SELECT {_CASE_FIELDS}, "
    "(SELECT Id, TextBody, MessageDate, FromName, FromAddress, Incoming "
    "FROM EmailMessages ORDER BY MessageDate DESC), "
    "(SELECT Id, CommentBody, CreatedDate, IsPublished, CreatedBy.Name "
    "FROM CaseComments ORDER BY CreatedDate DESC LIMIT 30) "
    "FROM Case WHERE CaseNumber = '{case_number}' LIMIT 1"
)

META_SOQL = f"SELECT {_CASE_FIELDS} FROM Case WHERE CaseNumber = '{{case_number}}' LIMIT 1"

EMAIL_SOQL = (
    "SELECT Id, TextBody, MessageDate, FromName, FromAddress, Incoming "
    "FROM EmailMessage WHERE ParentId = '{case_id}' ORDER BY MessageDate DESC"
)

COMMENTS_SOQL = (
    "SELECT Id, CommentBody, CreatedDate, IsPublished, CreatedBy.Name "
    "FROM CaseComment WHERE ParentId = '{case_id}' ORDER BY CreatedDate DESC LIMIT 30"
)

# Chatter feed — Salesforce blocks "FeedItem WHERE ParentId = ..." so we use
# the parent object Feeds relationship. Only TextPost and AdvancedTextPost have
# actual Body content; other types (EmailMessageEvent, MilestoneEvent, etc.)
# return Body: null and add no signal for internalDiscussion.
CHATTER_SOQL = (
    "SELECT (SELECT Id, Body, CreatedDate, CreatedBy.Name, Type "
    "FROM Feeds WHERE Type IN ('TextPost', 'AdvancedTextPost') "
    "ORDER BY CreatedDate DESC LIMIT 30) "
    "FROM Case WHERE Id = '{case_id}'"
)

# Fallback used when the primary query fails (e.g. ClosedDate not queryable in
# some org configs) — identical to CASE_SOQL minus ClosedDate.
_CASE_SOQL_FALLBACK = CASE_SOQL.replace("ClosedDate, ", "")


async def _run_soql(client: httpx.AsyncClient, query: str, instance_url: str, access_token: str) -> list[dict]:
    resp = await client.get(
        f"{instance_url}{_SOQL_PATH}",
        headers={"Authorization": f"Bearer {access_token}"},
        params={"q": query},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json().get("records", [])


def _trim_case(case: dict) -> dict:
    """Truncate large text fields so the payload stays within the LLM context budget."""
    emails = (case.get("EmailMessages") or {}).get("records", [])
    for email in emails[:_MAX_EMAILS]:
        body = email.get("TextBody") or ""
        if len(body) > _MAX_EMAIL_BODY_CHARS:
            email["TextBody"] = body[:_MAX_EMAIL_BODY_CHARS] + " [truncated]"
    if len(emails) > _MAX_EMAILS:
        case["EmailMessages"]["records"] = emails[:_MAX_EMAILS]

    comments = (case.get("CaseComments") or {}).get("records", [])
    for comment in comments:
        body = comment.get("CommentBody") or ""
        if len(body) > _MAX_COMMENT_BODY_CHARS:
            comment["CommentBody"] = body[:_MAX_COMMENT_BODY_CHARS] + " [truncated]"

    return case


async def fetch_case(case_number: str, instance_url: str, access_token: str) -> dict:
    """Fetch case + emails + internal comments + chatter feed via Salesforce REST API."""
    case_number = _soql_literal(case_number, "case_number")

    async with httpx.AsyncClient() as client:
        case = None
        for soql in (CASE_SOQL, _CASE_SOQL_FALLBACK):
            try:
                records = await _run_soql(client, soql.format(case_number=case_number), instance_url, access_token)
                if not records:
                    raise ValueError(f"Case {case_number} not found")
                case = records[0]
                break
            except httpx.HTTPStatusError:
                continue

        if case is None:
            case = await _fetch_meta_with_emails(client, case_number, instance_url, access_token)

        await _attach_internal_data(client, case, instance_url, access_token)

    _trim_case(case)
    return case


async def _fetch_meta_with_emails(client: httpx.AsyncClient, case_number: str, instance_url: str, access_token: str) -> dict:
    records = await _run_soql(client, META_SOQL.format(case_number=case_number), instance_url, access_token)
    if not records:
        raise ValueError(f"Case {case_number} not found in Salesforce")
    case = records[0]
    try:
        emails = await _run_soql(client, EMAIL_SOQL.format(case_id=_soql_literal(case["Id"], "case_id")), instance_url, access_token)
        case["EmailMessages"] = {"records": emails}
    except Exception:
        case["EmailMessages"] = {"records": []}
    return case


async def _attach_internal_data(client: httpx.AsyncClient, case: dict, instance_url: str, access_token: str) -> None:
    """Attach internal CaseComments and Chatter feed to an already-fetched case dict."""
    case_id = _soql_literal(case.get("Id", ""), "case_id")

    async def _fetch_comments():
        # Re-fetch CaseComments via standalone query when:
        # - key absent (fallback path), OR
        # - subquery returned null (Salesforce returns null not [] for empty relationships)
        # - subquery returned 0 records (standalone may pick up more if subquery had issues)
        existing_comments = case.get("CaseComments")
        if existing_comments and existing_comments.get("records"):
            return existing_comments["records"]
        try:
            return await _run_soql(client, COMMENTS_SOQL.format(case_id=case_id), instance_url, access_token)
        except Exception:
            return []

    async def _fetch_chatter():
        # Chatter TextPost / AdvancedTextPost — uses parent object Feeds subquery
        # because Salesforce blocks direct "FeedItem WHERE ParentId = ..." queries.
        try:
            records = await _run_soql(client, CHATTER_SOQL.format(case_id=case_id), instance_url, access_token)
            if records:
                return (records[0].get("Feeds") or {}).get("records", [])
        except Exception:
            pass
        return []

    comments, chatter_posts = await asyncio.gather(_fetch_comments(), _fetch_chatter())
    case["CaseComments"] = {"records": comments}
    case["ChatterFeed"] = {"records": chatter_posts}
