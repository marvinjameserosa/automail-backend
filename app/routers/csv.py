from typing import List, Dict, Any
import uuid
from datetime import datetime
import os
import io
import json

from fastapi import APIRouter, UploadFile, File, HTTPException, status, Body, Request
from fastapi.responses import JSONResponse, Response
import pandas as pd
from typing import Iterable

# Small in-memory store for uploaded DataFrames.
# Structure: { upload_id: { 'df': DataFrame, 'filename': str, 'created_at': isoformat } }
# Note: This is ephemeral and will be lost when the process restarts.
# For production use a persistent store (Redis, database, object storage).
dataframe_store: Dict[str, Dict[str, Any]] = {}

# Optional Redis for persistence. We use redis.asyncio if REDIS_URL is provided.
try:
    import redis.asyncio as aioredis
except Exception:
    aioredis = None  # type: ignore

# Redis client (async). If not configured or import fails, we keep using in-memory store.
redis_client = None
USE_REDIS = False
REDIS_URL = os.getenv("REDIS_URL") or os.getenv("REDIS_HOST")
# TTL in seconds for stored uploads (default 24 hours)
UPLOAD_TTL_SECONDS = int(os.getenv("UPLOAD_TTL_SECONDS", str(24 * 3600)))

router = APIRouter()

# Contract for /upload-csv
# - input: multipart/form-data with a file field named "file" (CSV)
# - output: JSON { filename: str, columns: List[str], rows: List[Dict[str, Any]], upload_id: str }
# - errors: returns 400 on parse errors or missing file

# NOTE: this module exposes `startup_event()` and `shutdown_event()` functions
# which should be registered on the main FastAPI app (see app/main.py).
async def startup_event():
    global redis_client, USE_REDIS
    if REDIS_URL and aioredis is not None:
        try:
            redis_client = aioredis.from_url(REDIS_URL)
            await redis_client.ping()
            USE_REDIS = True
            print("Connected to Redis for upload persistence")
        except Exception as e:
            redis_client = None
            USE_REDIS = False
            print(f"Redis unavailable, falling back to in-memory store: {e}")
    else:
        print("Redis not configured; using in-memory store for uploads")


async def shutdown_event():
    global redis_client
    if redis_client is not None:
        try:
            await redis_client.close()
        except Exception:
            pass


def _format_records_as_text(rows: Iterable[Dict[str, Any]]) -> str:
        """Convert list-of-dicts into a human-friendly numbered text format.

        Example:
        1:
            api_id: gst-...
            name: Carl
            email: carl@example.com
        2:
            ...
        """
        out_lines: List[str] = []
        # Ensure rows is a list of dicts
        seq = list(rows) if not isinstance(rows, dict) else [rows]
        for idx, rec in enumerate(seq, start=1):
                out_lines.append(f"{idx}:")
                for k, v in rec.items():
                        # Represent None as empty string similar to CSV blank cells
                        val = "" if v is None else str(v)
                        out_lines.append(f"  {k}: {val}")
                out_lines.append("")
        return "\n".join(out_lines)


@router.post("/upload-csv")
async def upload_csv(file: UploadFile = File(...), rows_only: bool = False, pretty: bool = False, as_text: bool = False):
    """Accept a CSV file upload, parse into a pandas DataFrame, store it in memory,
    and return basic JSON metadata and rows.

    Returns:
        JSON with keys: filename, columns, rows, upload_id

    Notes:
    - The in-memory store is `dataframe_store` and keyed by `upload_id` (UUID).
    - This endpoint intentionally returns the parsed rows so the frontend Table Editor
      can render them immediately. For very large CSVs you may want to paginate
      or only return a subset of rows.
    """
    if not file or not file.filename:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No file uploaded")

    # Only accept CSV-like files by content-type or filename extension check.
    # This is a basic check — adapt as needed for stricter validation.
    if not (file.filename.lower().endswith('.csv') or 'csv' in (file.content_type or '')):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Uploaded file is not a CSV")

    try:
        # Pandas can read from file-like objects. UploadFile.file is a SpooledTemporaryFile.
        # We read into a DataFrame and sanitize numpy types for JSON encoding.
        df = pd.read_csv(file.file)
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Failed to parse CSV: {exc}")

    # Generate an upload id and keep the DataFrame in memory for later API calls.
    upload_id = str(uuid.uuid4())
    dataframe_store[upload_id] = {
        "df": df,
        "filename": file.filename,
        "created_at": datetime.utcnow().isoformat() + "Z",
    }

    # If Redis is configured, persist the CSV text and metadata there as well.
    # We store CSV text (index=False) under key upload:{upload_id}:csv and metadata under upload:{upload_id}:meta
    if USE_REDIS and redis_client is not None:
        try:
            csv_text = df.to_csv(index=False)
            await redis_client.set(f"upload:{upload_id}:csv", csv_text, ex=UPLOAD_TTL_SECONDS)
            meta = {"filename": file.filename, "created_at": dataframe_store[upload_id]["created_at"]}
            await redis_client.set(f"upload:{upload_id}:meta", json.dumps(meta), ex=UPLOAD_TTL_SECONDS)
        except Exception:
            # failure to persist should not block the upload response; keep in-memory store
            pass

    # Prepare rows and columns for JSON response. Convert numpy scalars to Python natives.
    try:
        safe_df = df.where(pd.notnull(df), None)
        # Convert numpy types to native python types via `.item()` when available.
        def _to_py(x):
            try:
                if hasattr(x, "item"):
                    return x.item()
            except Exception:
                pass
            return x

        rows = (
            safe_df.astype(object).where(pd.notnull(safe_df), None).applymap(_to_py).to_dict(orient='records')
        )
        columns = list(df.columns.astype(str))
    except Exception:
        # Fallback: use pandas' built-in conversion (may contain numpy types handled by FastAPI encoder)
        rows = df.to_dict(orient='records')
        columns = list(df.columns.astype(str))

    if rows_only:
        # If caller asked for rows-only, return a single object for one-row payloads,
        # otherwise return the list of record objects directly. Support pretty printing
        # and an optional human-friendly plain-text view (`as_text`).
        out = rows[0] if isinstance(rows, list) and len(rows) == 1 else rows
        if as_text:
            text = _format_records_as_text(out)
            return Response(content=text, media_type="text/plain; charset=utf-8")
        if pretty:
            return Response(content=json.dumps(out, indent=2), media_type="application/json")
        return JSONResponse(content=out)

    response = {
        "filename": file.filename,
        "columns": columns,
        "rows": rows,
        "upload_id": upload_id,
    }

    if as_text and rows:
        # Return the whole dataset as plain text
        text = _format_records_as_text(rows)
        return Response(content=text, media_type="text/plain; charset=utf-8")

    if pretty:
        return Response(content=json.dumps(response, indent=2), media_type="application/json")

    return JSONResponse(content=response)


@router.post("/upload-json")
async def upload_json(request: Request, file: UploadFile = File(None), payload: dict | list | None = Body(None), rows_only: bool = False, pretty: bool = False, as_text: bool = False):
    """Accept JSON either as a file upload (multipart/form-data) or as an application/json body.

    The endpoint expects either:
    - A JSON array of objects (rows), e.g. [{...}, {...}], or
    - A JSON object with a top-level key containing the rows, commonly `items` or `rows`, e.g. {"items": [...]}

    It converts the JSON into a pandas DataFrame, stores it in the same in-memory/Redis store, and
    returns the same response shape as `/upload-csv` (filename, columns, rows, upload_id).
    """
    # Obtain JSON data from either uploaded file or request body
    data = None
    filename = None
    if file is not None and file.filename:
        # Read uploaded JSON file
        try:
            raw = await file.read()
            text = raw.decode('utf-8') if isinstance(raw, (bytes, bytearray)) else str(raw)
            data = json.loads(text)
            filename = file.filename
        except Exception as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Failed to parse uploaded JSON: {exc}")
    elif payload is not None:
        data = payload
        filename = "payload.json"
    else:
        # In some cases, when combining File and Body params, FastAPI may not bind the JSON body to `payload`.
        # As a fallback, attempt to parse the raw request body as JSON.
        try:
            if request.headers.get("content-type", "").startswith("application/json"):
                data = await request.json()
                filename = "payload.json"
            else:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No JSON file uploaded or JSON body provided")
        except Exception:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No JSON file uploaded or JSON body provided")

    # Normalize to a list of records
    rows_list = None
    if isinstance(data, list):
        rows_list = data
    elif isinstance(data, dict):
        # Accepted keys: items, rows, data
        for key in ("items", "rows", "data"):
            if key in data and isinstance(data[key], list):
                rows_list = data[key]
                break
        # If dict is a mapping of scalar columns to lists, convert to DataFrame directly
        if rows_list is None:
            # try to interpret dict-of-lists or single-record
            # If values are lists of equal length -> create DataFrame from dict
            try:
                df_try = pd.DataFrame(data)
                # If df_try has more than 0 rows, use it
                if len(df_try) > 0:
                    df = df_try
                    rows_list = None
                else:
                    # fallback to treat dict as single row
                    rows_list = [data]
            except Exception:
                rows_list = [data]

    # If we haven't created df yet from dict-of-lists, create from rows_list
    if 'df' not in locals():
        if rows_list is None:
            rows_list = []
        try:
            df = pd.json_normalize(rows_list)
        except Exception as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Failed to convert JSON to DataFrame: {exc}")

    # Store DataFrame
    upload_id = str(uuid.uuid4())
    dataframe_store[upload_id] = {
        "df": df,
        "filename": filename or f"upload-{upload_id}.json",
        "created_at": datetime.utcnow().isoformat() + "Z",
    }

    # Persist to Redis if configured (store JSON text and metadata)
    if USE_REDIS and redis_client is not None:
        try:
            json_text = json.dumps(rows_list if rows_list is not None else json.loads(df.to_json(orient='records')))
            await redis_client.set(f"upload:{upload_id}:json", json_text, ex=UPLOAD_TTL_SECONDS)
            meta = {"filename": dataframe_store[upload_id]["filename"], "created_at": dataframe_store[upload_id]["created_at"]}
            await redis_client.set(f"upload:{upload_id}:meta", json.dumps(meta), ex=UPLOAD_TTL_SECONDS)
        except Exception:
            pass

    # Prepare response (convert types)
    try:
        safe_df = df.where(pd.notnull(df), None)

        def _to_py(x):
            try:
                if hasattr(x, "item"):
                    return x.item()
            except Exception:
                pass
            return x

        rows = (
            safe_df.astype(object).where(pd.notnull(safe_df), None).applymap(_to_py).to_dict(orient='records')
        )
        columns = list(df.columns.astype(str))
    except Exception:
        rows = df.to_dict(orient='records')
        columns = list(df.columns.astype(str))

    if rows_only:
        out = rows[0] if isinstance(rows, list) and len(rows) == 1 else rows
        if as_text:
            text = _format_records_as_text(out)
            return Response(content=text, media_type="text/plain; charset=utf-8")
        if pretty:
            return Response(content=json.dumps(out, indent=2), media_type="application/json")
        return JSONResponse(content=out)

    response = {
        "filename": dataframe_store[upload_id]["filename"],
        "columns": columns,
        "rows": rows,
        "upload_id": upload_id,
    }

    if as_text and rows:
        text = _format_records_as_text(rows)
        return Response(content=text, media_type="text/plain; charset=utf-8")

    if pretty:
        return Response(content=json.dumps(response, indent=2), media_type="application/json")

    return JSONResponse(content=response)



@router.get("/dataframes/{upload_id}")
async def get_dataframe(upload_id: str, pretty: bool = False, rows_only: bool = False, as_text: bool = False):
    """Retrieve a previously uploaded DataFrame by upload_id.

    Returns the same shape as the upload response: filename, columns, rows, upload_id.
    """
    # Try Redis first (if enabled). If not found, fall back to in-memory store.
    df = None
    filename = None
    if USE_REDIS and redis_client is not None:
        try:
            csv_bytes = await redis_client.get(f"upload:{upload_id}:csv")
            if csv_bytes:
                # csv_bytes may be stored as bytes or str
                csv_text = csv_bytes.decode() if isinstance(csv_bytes, (bytes, bytearray)) else str(csv_bytes)
                df = pd.read_csv(io.StringIO(csv_text))
                meta_raw = await redis_client.get(f"upload:{upload_id}:meta")
                if meta_raw:
                    try:
                        meta = json.loads(meta_raw.decode() if isinstance(meta_raw, (bytes, bytearray)) else str(meta_raw))
                        filename = meta.get("filename")
                    except Exception:
                        filename = None
        except Exception:
            # Redis failure — fall back to in-memory
            df = None

    if df is None:
        stored = dataframe_store.get(upload_id)
        if not stored:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="upload_id not found")
        df = stored["df"]
        filename = filename or stored.get("filename")

    try:
        safe_df = df.where(pd.notnull(df), None)

        def _to_py(x):
            try:
                if hasattr(x, "item"):
                    return x.item()
            except Exception:
                pass
            return x

        rows = (
            safe_df.astype(object).where(pd.notnull(safe_df), None).applymap(_to_py).to_dict(orient='records')
        )
        columns = list(df.columns.astype(str))
    except Exception:
        rows = df.to_dict(orient='records')
        columns = list(df.columns.astype(str))

    payload = {
        "filename": filename,
        "columns": columns,
        "rows": rows,
        "upload_id": upload_id,
    }

    if rows_only:
        # return just the rows (single object if exactly one row)
        out = rows[0] if isinstance(rows, list) and len(rows) == 1 else rows
        if as_text:
            text = _format_records_as_text(out)
            return Response(content=text, media_type="text/plain; charset=utf-8")
        if pretty:
            return Response(content=json.dumps(out, indent=2), media_type="application/json")
        return JSONResponse(content=out)

    if as_text:
        # Return the whole payload rows as plain text (human-friendly)
        text = _format_records_as_text(rows)
        return Response(content=text, media_type="text/plain; charset=utf-8")

    if pretty:
        # Return indented JSON string for easier browser viewing
        return Response(content=json.dumps(payload, indent=2), media_type="application/json")
    return JSONResponse(content=payload)


@router.get("/dataframes")
async def list_dataframes(pretty: bool = False, rows_only: bool = False, as_text: bool = False):
    """Return the most-recent upload's contents by default so callers do not need to supply an upload_id.

    Supports the same view flags as `GET /dataframes/{upload_id}`: `pretty`, `rows_only`, and `as_text`.
    If no uploads exist, returns an empty items list (same shape as previous behavior).
    """
    # Reconstruct items (like get_latest) to find the most recent upload id
    items = []
    if USE_REDIS and redis_client is not None:
        try:
            keys = await redis_client.keys("upload:*:meta")
            for k in keys:
                try:
                    raw = await redis_client.get(k)
                    if not raw:
                        continue
                    s = raw.decode() if isinstance(raw, (bytes, bytearray)) else str(raw)
                    meta = json.loads(s)
                    k_str = k.decode() if isinstance(k, (bytes, bytearray)) else str(k)
                    parts = k_str.split(":")
                    if len(parts) >= 3:
                        upload_id = parts[1]
                        items.append({"upload_id": upload_id, "filename": meta.get("filename"), "created_at": meta.get("created_at")})
                except Exception:
                    continue
        except Exception:
            pass

    existing = {it["upload_id"] for it in items}
    for uid, meta in dataframe_store.items():
        if uid in existing:
            continue
        items.append({"upload_id": uid, "filename": meta.get("filename"), "created_at": meta.get("created_at")})

    if not items:
        payload = {"items": []}
        if pretty:
            return Response(content=json.dumps(payload, indent=2), media_type="application/json")
        return JSONResponse(content=payload)

    # sort by created_at descending and pick latest
    items_sorted = sorted(items, key=lambda x: x.get("created_at", ""), reverse=True)
    latest_id = items_sorted[0]["upload_id"]
    # delegate to get_dataframe to produce consistent output
    return await get_dataframe(latest_id, pretty=pretty, rows_only=rows_only, as_text=as_text)


@router.get("/dataframes/latest")
async def get_latest(pretty: bool = False, rows_only: bool = False, as_text: bool = False):
    """Return the most-recent upload. Supports same view flags as GET /dataframes/{id}.

    This endpoint picks the latest item by `created_at` from Redis (if available)
    and the in-memory store, then dispatches to get_dataframe for a consistent view.
    """
    # Reconstruct the items list similarly to list_dataframes
    items = []
    if USE_REDIS and redis_client is not None:
        try:
            keys = await redis_client.keys("upload:*:meta")
            for k in keys:
                try:
                    raw = await redis_client.get(k)
                    if not raw:
                        continue
                    s = raw.decode() if isinstance(raw, (bytes, bytearray)) else str(raw)
                    meta = json.loads(s)
                    k_str = k.decode() if isinstance(k, (bytes, bytearray)) else str(k)
                    parts = k_str.split(":")
                    if len(parts) >= 3:
                        upload_id = parts[1]
                        items.append({"upload_id": upload_id, "filename": meta.get("filename"), "created_at": meta.get("created_at")})
                except Exception:
                    continue
        except Exception:
            pass

    existing = {it["upload_id"] for it in items}
    for uid, meta in dataframe_store.items():
        if uid in existing:
            continue
        items.append({"upload_id": uid, "filename": meta.get("filename"), "created_at": meta.get("created_at")})

    if not items:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="no uploads found")

    # sort by created_at (ISO strings sort lexicographically)
    items_sorted = sorted(items, key=lambda x: x.get("created_at", ""), reverse=True)
    latest_id = items_sorted[0]["upload_id"]
    return await get_dataframe(latest_id, pretty=pretty, rows_only=rows_only, as_text=as_text)


@router.delete("/dataframes/{upload_id}")
async def delete_dataframe(upload_id: str):
    """Remove a stored DataFrame from the in-memory store."""
    deleted = False
    # Try delete from Redis if available
    if USE_REDIS and redis_client is not None:
        try:
            await redis_client.delete(f"upload:{upload_id}:csv")
            await redis_client.delete(f"upload:{upload_id}:meta")
            deleted = True
        except Exception:
            # ignore redis errors and try in-memory
            deleted = False

    if upload_id in dataframe_store:
        del dataframe_store[upload_id]
        deleted = True

    if deleted:
        return JSONResponse(content={"deleted": upload_id})

    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="upload_id not found")


# Do not include the example router (UI placeholder). We only expose the CSV-related
# endpoints implemented in this module: /upload-csv, /dataframes, /dataframes/{id}.

#how to run           Start-Process "http://localhost:8000/dataframes?as_text=1"
