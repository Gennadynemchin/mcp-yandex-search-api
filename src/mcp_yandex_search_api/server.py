"""MCP server exposing Yandex Search API image-search-by-text as a tool."""

from __future__ import annotations

import base64
import os
import re
from typing import Any, Literal
from xml.etree import ElementTree as ET

import httpx
from mcp.server.fastmcp import FastMCP

YANDEX_SEARCH_IMAGE_URL = "https://searchapi.api.cloud.yandex.net/v2/image/search"

SearchType = Literal[
    "SEARCH_TYPE_RU",
    "SEARCH_TYPE_TR",
    "SEARCH_TYPE_COM",
    "SEARCH_TYPE_KK",
    "SEARCH_TYPE_BE",
    "SEARCH_TYPE_UZ",
]
FamilyMode = Literal["FAMILY_MODE_MODERATE", "FAMILY_MODE_NONE", "FAMILY_MODE_STRICT"]
FixTypoMode = Literal["FIX_TYPO_MODE_ON", "FIX_TYPO_MODE_OFF"]
ImageFormat = Literal["IMAGE_FORMAT_JPEG", "IMAGE_FORMAT_GIF", "IMAGE_FORMAT_PNG"]
ImageSize = Literal[
    "IMAGE_SIZE_ENORMOUS",
    "IMAGE_SIZE_LARGE",
    "IMAGE_SIZE_MEDIUM",
    "IMAGE_SIZE_SMALL",
    "IMAGE_SIZE_TINY",
    "IMAGE_SIZE_WALLPAPER",
]
ImageOrientation = Literal[
    "IMAGE_ORIENTATION_VERTICAL",
    "IMAGE_ORIENTATION_HORIZONTAL",
    "IMAGE_ORIENTATION_SQUARE",
]
ImageColor = Literal[
    "IMAGE_COLOR_COLOR",
    "IMAGE_COLOR_GRAYSCALE",
    "IMAGE_COLOR_RED",
    "IMAGE_COLOR_ORANGE",
    "IMAGE_COLOR_YELLOW",
    "IMAGE_COLOR_GREEN",
    "IMAGE_COLOR_CYAN",
    "IMAGE_COLOR_BLUE",
    "IMAGE_COLOR_VIOLET",
    "IMAGE_COLOR_WHITE",
    "IMAGE_COLOR_BLACK",
]

mcp = FastMCP("yandex-search-api")


def _get_credentials() -> tuple[str, str]:
    folder_id = os.environ.get("YANDEX_FOLDER_ID")
    api_key = os.environ.get("YANDEX_API_KEY")
    iam_token = os.environ.get("YANDEX_IAM_TOKEN")
    if not folder_id:
        raise RuntimeError("YANDEX_FOLDER_ID environment variable is not set")
    if not api_key and not iam_token:
        raise RuntimeError(
            "Either YANDEX_API_KEY or YANDEX_IAM_TOKEN environment variable must be set"
        )
    if api_key:
        return folder_id, f"Api-Key {api_key}"
    return folder_id, f"Bearer {iam_token}"


def _parse_image_results(xml_text: str, limit: int) -> list[dict[str, Any]]:
    """Parse Yandex image search XML response into a compact list."""
    items: list[dict[str, Any]] = []
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return items

    for doc in root.iter("doc"):
        url_el = doc.find("url")
        image_el = doc.find("image-properties/image-source-data/image-source/url")
        if image_el is None:
            image_el = doc.find(".//image-source/url")
        thumb_el = doc.find(".//thumbnail/url")
        title_el = doc.find("title")
        passages = [p.text or "" for p in doc.iter("passage")]

        items.append(
            {
                "page_url": (url_el.text if url_el is not None else None),
                "image_url": (image_el.text if image_el is not None else None),
                "thumbnail_url": (thumb_el.text if thumb_el is not None else None),
                "title": _strip_tags(title_el) if title_el is not None else None,
                "passages": passages or None,
            }
        )
        if len(items) >= limit:
            break
    return items


def _strip_tags(el: ET.Element) -> str:
    text = ET.tostring(el, encoding="unicode", method="text")
    return re.sub(r"\s+", " ", text).strip()


@mcp.tool()
async def search_images(
    query: str,
    page: int = 0,
    docs_on_page: int = 10,
    search_type: SearchType = "SEARCH_TYPE_RU",
    family_mode: FamilyMode = "FAMILY_MODE_MODERATE",
    fix_typo_mode: FixTypoMode = "FIX_TYPO_MODE_ON",
    image_format: ImageFormat | None = None,
    size: ImageSize | None = None,
    orientation: ImageOrientation | None = None,
    color: ImageColor | None = None,
    site: str | None = None,
    user_agent: str | None = None,
    return_raw_xml: bool = False,
) -> dict[str, Any]:
    """Search images in Yandex Images index by text query.

    Returns a list of image results parsed from the Yandex Search API XML
    response. Authentication is taken from environment variables
    YANDEX_FOLDER_ID and YANDEX_API_KEY (or YANDEX_IAM_TOKEN).

    Args:
        query: Search query text (max 400 chars).
        page: Page number, 0-based.
        docs_on_page: Results per page (1-60).
        search_type: Language/region of search.
        family_mode: Adult content filtering mode.
        fix_typo_mode: Typo correction mode.
        image_format: Restrict by image format (JPEG/GIF/PNG).
        size: Restrict by image size class.
        orientation: Restrict by image orientation.
        color: Restrict by dominant color.
        site: Restrict search to a single domain.
        user_agent: Optional User-Agent override (e.g. mobile UA).
        return_raw_xml: If true — include the decoded XML in the response.
    """
    folder_id, auth_header = _get_credentials()

    image_spec: dict[str, Any] = {}
    if image_format:
        image_spec["format"] = image_format
    if size:
        image_spec["size"] = size
    if orientation:
        image_spec["orientation"] = orientation
    if color:
        image_spec["color"] = color

    body: dict[str, Any] = {
        "query": {
            "searchType": search_type,
            "queryText": query,
            "familyMode": family_mode,
            "page": str(page),
            "fixTypoMode": fix_typo_mode,
        },
        "folderId": folder_id,
        "docsOnPage": str(max(1, min(60, docs_on_page))),
    }
    if image_spec:
        body["imageSpec"] = image_spec
    if site:
        body["site"] = site
    if user_agent:
        body["userAgent"] = user_agent

    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(
            YANDEX_SEARCH_IMAGE_URL,
            headers={
                "Authorization": auth_header,
                "Content-Type": "application/json",
            },
            json=body,
        )

    if resp.status_code >= 400:
        raise RuntimeError(
            f"Yandex Search API returned {resp.status_code}: {resp.text}"
        )

    data = resp.json()
    raw_data_b64 = data.get("rawData")
    if not raw_data_b64:
        return {"results": [], "raw": data}

    xml_text = base64.b64decode(raw_data_b64).decode("utf-8", errors="replace")
    results = _parse_image_results(xml_text, docs_on_page)

    out: dict[str, Any] = {"query": query, "page": page, "results": results}
    if return_raw_xml:
        out["raw_xml"] = xml_text
    return out


def main() -> None:
    """Run the MCP server over stdio."""
    mcp.run()


if __name__ == "__main__":
    main()
