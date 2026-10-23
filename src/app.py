import json
import os
import time
import uuid
from datetime import date
from decimal import Decimal

import boto3

table = boto3.resource("dynamodb").Table(os.environ["TABLE_NAME"])
STATUSES = {"Planned", "Applied", "Interview", "Offer", "Rejected"}
MAX_ITEMS = 200


def to_json(value):
    """DynamoDB returns numbers as Decimal, which json can't handle by default."""
    if isinstance(value, Decimal):
        return int(value) if value == value.to_integral_value() else float(value)
    raise TypeError(f"Cannot serialise {type(value)}")


def respond(code, body=None):
    return {
        "statusCode": code,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(body if body is not None else {}, default=to_json),
    }


def clean(data, partial=False):
    """Validate and trim the fields we accept; raise ValueError on bad input."""
    out = {}
    if "organisation" in data or not partial:
        org = str(data.get("organisation", "")).strip()
        if not org or len(org) > 100:
            raise ValueError("Organisation is required (max 100 characters).")
        out["organisation"] = org
    if "role" in data or not partial:
        out["role"] = str(data.get("role", "")).strip()[:100]
    if "status" in data or not partial:
        status = data.get("status", "Planned")
        if status not in STATUSES:
            raise ValueError("Status must be one of: " + ", ".join(sorted(STATUSES)))
        out["status"] = status
    if "deadline" in data or not partial:
        deadline = str(data.get("deadline", "")).strip()
        if deadline:
            date.fromisoformat(deadline)  # raises ValueError if not YYYY-MM-DD
        out["deadline"] = deadline
    if "notes" in data or not partial:
        out["notes"] = str(data.get("notes", "")).strip()[:500]
    return out


def handler(event, context):
    method = event["requestContext"]["http"]["method"]
    item_id = (event.get("pathParameters") or {}).get("id")
    try:
        if method == "GET":
            items = table.scan(Limit=MAX_ITEMS).get("Items", [])
            items.sort(key=lambda i: (i.get("deadline") or "9999-99-99", i["organisation"]))
            return respond(200, items)

        if method == "POST":
            if table.scan(Select="COUNT", Limit=MAX_ITEMS)["Count"] >= MAX_ITEMS:
                return respond(400, {"error": "Limit reached. Delete an entry first."})
            item = clean(json.loads(event.get("body") or "{}"))
            item.update(id=str(uuid.uuid4()), createdAt=int(time.time()))
            table.put_item(Item=item)
            return respond(201, item)

        if method == "PUT" and item_id:
            existing = table.get_item(Key={"id": item_id}).get("Item")
            if not existing:
                return respond(404, {"error": "Not found."})
            existing.update(clean(json.loads(event.get("body") or "{}"), partial=True))
            table.put_item(Item=existing)
            return respond(200, existing)

        if method == "DELETE" and item_id:
            table.delete_item(Key={"id": item_id})
            return respond(204)

        return respond(405, {"error": "Method not allowed."})
    except (ValueError, json.JSONDecodeError) as err:
        return respond(400, {"error": str(err)})
    except Exception as err:  # log the details, return a generic message
        print("Unhandled error:", repr(err))
        return respond(500, {"error": "Something went wrong. Try again."})
