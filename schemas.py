"""
Database Schemas

Define your MongoDB collection schemas here using Pydantic models.
These schemas are used for data validation in your application.

Each Pydantic model represents a collection in your database.
Model name is converted to lowercase for the collection name:
- User -> "user" collection
- Product -> "product" collection
- BlogPost -> "blogs" collection
"""

from pydantic import BaseModel, Field, HttpUrl
from typing import Optional, List
from datetime import datetime

# Example schemas (replace with your own):

class User(BaseModel):
    """
    Users collection schema
    Collection name: "user" (lowercase of class name)
    """
    name: str = Field(..., description="Full name")
    email: str = Field(..., description="Email address")
    address: str = Field(..., description="Address")
    age: Optional[int] = Field(None, ge=0, le=120, description="Age in years")
    is_active: bool = Field(True, description="Whether user is active")

class Product(BaseModel):
    """
    Products collection schema
    Collection name: "product" (lowercase of class name)
    """
    title: str = Field(..., description="Product title")
    description: Optional[str] = Field(None, description="Product description")
    price: float = Field(..., ge=0, description="Price in dollars")
    category: str = Field(..., description="Product category")
    in_stock: bool = Field(True, description="Whether product is in stock")

# --------------------------------------------------
# Core Content Hub schemas (used by the CMS)

class Category(BaseModel):
    """
    Categories for grouping posts
    Collection name: "category"
    """
    name: str = Field(..., description="Category name")
    slug: str = Field(..., description="URL-safe unique slug")
    description: Optional[str] = Field(None, description="Category description")

class Post(BaseModel):
    """
    Post content schema
    Collection name: "post"
    """
    title: str = Field(..., description="Post title")
    slug: str = Field(..., description="URL-safe unique slug")
    excerpt: Optional[str] = Field(None, description="Short summary")
    content: str = Field(..., description="Rich content (HTML/Markdown)")
    image_url: Optional[str] = Field(None, description="Lead image URL")
    category_slug: Optional[str] = Field(None, description="Associated category slug")
    tags: Optional[List[str]] = Field(default=None, description="List of tags")
    status: str = Field("draft", description="draft | published")
    author: Optional[str] = Field(None, description="Author name")
    published_at: Optional[datetime] = Field(None, description="Publish timestamp (UTC)")
