from pydantic import BaseModel
from typing import Optional, List

class UserCreate(BaseModel):
    name: str
    email: str
    role: str
    job_title: str 
    password: str

class ContentCreate(BaseModel):
    name: str
    price: float
    status: str
    content_type: str

class SplitCreate(BaseModel):
    user_id: int
    content_id: int
    split_percentage: float

class UserUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    job_title: Optional[str] = None 
    password: Optional[str] = None

class SplitUpdate(BaseModel):
    user_id: int
    percentage: float

class ContentUpdate(BaseModel):
    name: Optional[str] = None
    price: Optional[float] = None
    status: Optional[str] = None
    content_type: Optional[str] = None
    splits: Optional[List[SplitUpdate]] = None

# ==========================================
# SCHEMA UNTUK CMS LANDING PAGE
# ==========================================

class CMSCommissionCreate(BaseModel):
    title: Optional[str] = None        
    description: Optional[str] = None  
    thumbnail_url: str
    year: str
    gallery_urls: Optional[str] = ""
    link: Optional[str] = None

class CMSCommissionUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    thumbnail_url: Optional[str] = None
    year: Optional[str] = None  # <-- TAMBAHAN BARU: Tahun project
    gallery_urls: Optional[str] = None
    link: Optional[str] = None

# 2. MARKETPLACE
class CMSMarketplaceCreate(BaseModel):
    title: str
    content_type: str # <-- Ini menggantikan description
    image_url: str
    price_minecoin: int
    link: Optional[str] = None

class CMSMarketplaceUpdate(BaseModel):
    title: Optional[str] = None
    content_type: Optional[str] = None # <-- Ini menggantikan description
    image_url: Optional[str] = None
    price_minecoin: Optional[int] = None
    link: Optional[str] = None

# 3. PREMADE ASSETS
class CMSPremadeCreate(BaseModel):
    title: str
    category: str      # <-- TAMBAHAN BARU
    description: Optional[str] = None
    image_url: str
    price_usd: float
    link: Optional[str] = None

class CMSPremadeUpdate(BaseModel):
    title: Optional[str] = None
    category: Optional[str] = None # <-- TAMBAHAN BARU
    description: Optional[str] = None
    image_url: Optional[str] = None
    price_usd: Optional[float] = None
    link: Optional[str] = None
    
# TEAM, EXHIBITION, CLIENTS
class CMSTeamCreate(BaseModel):
    name: str
    role: str
    image_url: Optional[str] = None
    bio: Optional[str] = None
    link_x: Optional[str] = None
    link_linkedin: Optional[str] = None
    link_instagram: Optional[str] = None
    link_website: Optional[str] = None

class CMSTeamUpdate(BaseModel):
    name: Optional[str] = None
    role: Optional[str] = None
    image_url: Optional[str] = None
    bio: Optional[str] = None
    link_x: Optional[str] = None
    link_linkedin: Optional[str] = None
    link_instagram: Optional[str] = None
    link_website: Optional[str] = None

class CMSExhibitionCreate(BaseModel):
    image_url: str
    link: Optional[str] = None

class CMSExhibitionUpdate(BaseModel):
    image_url: Optional[str] = None
    link: Optional[str] = None

class CMSClientCreate(BaseModel):
    img: str
    link: Optional[str] = None

class CMSClientUpdate(BaseModel):
    img: Optional[str] = None
    link: Optional[str] = None