import os
from typing import List, Optional
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from datetime import datetime, timezone
from bson import ObjectId

from database import db, create_document, get_documents
from schemas import Post, Category

app = FastAPI(title="Core Content Hub API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Utility to convert Mongo docs to JSON safe

def serialize_doc(doc):
    if not doc:
        return doc
    d = dict(doc)
    if "_id" in d:
        d["id"] = str(d.pop("_id"))
    # Convert datetimes
    for k, v in list(d.items()):
        if isinstance(v, datetime):
            d[k] = v.astimezone(timezone.utc).isoformat()
    return d


@app.get("/")
def read_root():
    return {"message": "Core Content Hub API running"}


@app.get("/test")
def test_database():
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }
    try:
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
            response["database_name"] = db.name if hasattr(db, 'name') else "✅ Connected"
            response["connection_status"] = "Connected"
            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️  Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️  Available but not initialized"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"
    return response


# Admin models for input (separate from DB schema if needed)
class PostCreate(Post):
    pass

class PostUpdate(BaseModel):
    title: Optional[str] = None
    slug: Optional[str] = None
    excerpt: Optional[str] = None
    content: Optional[str] = None
    image_url: Optional[str] = None
    category_slug: Optional[str] = None
    tags: Optional[List[str]] = None
    status: Optional[str] = None
    author: Optional[str] = None
    published_at: Optional[datetime] = None

class CategoryCreate(Category):
    pass

class CategoryUpdate(BaseModel):
    name: Optional[str] = None
    slug: Optional[str] = None
    description: Optional[str] = None


# ----------------------
# Admin (CRUD) endpoints
# ----------------------

@app.post("/api/admin/categories")
def create_category(payload: CategoryCreate):
    existing = db["category"].find_one({"slug": payload.slug}) if db else None
    if existing:
        raise HTTPException(status_code=400, detail="Category slug already exists")
    cat_id = create_document("category", payload)
    doc = db["category"].find_one({"_id": ObjectId(cat_id)})
    return serialize_doc(doc)

@app.get("/api/admin/categories")
def list_categories():
    docs = get_documents("category")
    return [serialize_doc(d) for d in docs]

@app.patch("/api/admin/categories/{id}")
def update_category(id: str, payload: CategoryUpdate):
    if not ObjectId.is_valid(id):
        raise HTTPException(status_code=400, detail="Invalid id")
    update = {k: v for k, v in payload.model_dump(exclude_unset=True).items()}
    if not update:
        return {"updated": False}
    update["updated_at"] = datetime.now(timezone.utc)
    res = db["category"].update_one({"_id": ObjectId(id)}, {"$set": update})
    doc = db["category"].find_one({"_id": ObjectId(id)})
    return serialize_doc(doc) if res.matched_count else HTTPException(status_code=404, detail="Not found")

@app.delete("/api/admin/categories/{id}")
def delete_category(id: str):
    if not ObjectId.is_valid(id):
        raise HTTPException(status_code=400, detail="Invalid id")
    res = db["category"].delete_one({"_id": ObjectId(id)})
    return {"deleted": res.deleted_count == 1}


@app.post("/api/admin/posts")
def create_post(payload: PostCreate):
    # Enforce unique slug
    existing = db["post"].find_one({"slug": payload.slug}) if db else None
    if existing:
        raise HTTPException(status_code=400, detail="Post slug already exists")
    data = payload.model_dump()
    if data.get("status") == "published" and not data.get("published_at"):
        data["published_at"] = datetime.now(timezone.utc)
    post_id = create_document("post", data)
    doc = db["post"].find_one({"_id": ObjectId(post_id)})
    return serialize_doc(doc)

@app.get("/api/admin/posts")
def list_posts_admin(status: Optional[str] = Query(None), q: Optional[str] = Query(None)):
    filt = {}
    if status:
        filt["status"] = status
    if q:
        filt["$or"] = [
            {"title": {"$regex": q, "$options": "i"}},
            {"excerpt": {"$regex": q, "$options": "i"}},
            {"content": {"$regex": q, "$options": "i"}},
        ]
    docs = db["post"].find(filt).sort("created_at", -1)
    return [serialize_doc(d) for d in docs]

@app.get("/api/admin/posts/{id}")
def get_post_admin(id: str):
    if not ObjectId.is_valid(id):
        raise HTTPException(status_code=400, detail="Invalid id")
    doc = db["post"].find_one({"_id": ObjectId(id)})
    if not doc:
        raise HTTPException(status_code=404, detail="Not found")
    return serialize_doc(doc)

@app.patch("/api/admin/posts/{id}")
def update_post(id: str, payload: PostUpdate):
    if not ObjectId.is_valid(id):
        raise HTTPException(status_code=400, detail="Invalid id")
    update = {k: v for k, v in payload.model_dump(exclude_unset=True).items()}
    if not update:
        return {"updated": False}
    if update.get("status") == "published" and not update.get("published_at"):
        update["published_at"] = datetime.now(timezone.utc)
    update["updated_at"] = datetime.now(timezone.utc)
    res = db["post"].update_one({"_id": ObjectId(id)}, {"$set": update})
    doc = db["post"].find_one({"_id": ObjectId(id)})
    return serialize_doc(doc) if res.matched_count else HTTPException(status_code=404, detail="Not found")

@app.delete("/api/admin/posts/{id}")
def delete_post(id: str):
    if not ObjectId.is_valid(id):
        raise HTTPException(status_code=400, detail="Invalid id")
    res = db["post"].delete_one({"_id": ObjectId(id)})
    return {"deleted": res.deleted_count == 1}


# ----------------------
# Public API endpoints
# ----------------------

@app.get("/api/posts")
def list_posts_public(page: int = 1, page_size: int = 10, category: Optional[str] = None, tag: Optional[str] = None):
    filt = {"status": "published"}
    if category:
        filt["category_slug"] = category
    if tag:
        filt["tags"] = {"$in": [tag]}
    skip = (page - 1) * page_size
    cursor = db["post"].find(filt).sort("published_at", -1).skip(skip).limit(page_size)
    items = [serialize_doc(d) for d in cursor]
    total = db["post"].count_documents(filt)
    return {"items": items, "page": page, "page_size": page_size, "total": total}

@app.get("/api/posts/{slug}")
def get_post_by_slug(slug: str):
    doc = db["post"].find_one({"slug": slug, "status": "published"})
    if not doc:
        raise HTTPException(status_code=404, detail="Not found")
    return serialize_doc(doc)

@app.get("/api/categories")
def list_categories_public():
    docs = get_documents("category")
    return [serialize_doc(d) for d in docs]


# ----------------------
# WordPress Syndication endpoints
# ----------------------

class WPFeedItem(BaseModel):
    id: str
    title: str
    slug: str
    excerpt: Optional[str] = None
    content: str
    image_url: Optional[str] = None
    category_slug: Optional[str] = None
    tags: Optional[List[str]] = None
    author: Optional[str] = None
    published_at: Optional[str] = None

@app.get("/api/wp/feed", response_model=List[WPFeedItem])
def wp_feed(limit: int = 50):
    filt = {"status": "published"}
    cursor = db["post"].find(filt).sort("published_at", -1).limit(limit)
    items: List[WPFeedItem] = []
    for d in cursor:
        s = serialize_doc(d)
        items.append(WPFeedItem(**s))
    return items


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
