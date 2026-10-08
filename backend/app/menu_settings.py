from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy import update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .database import get_db
from .models import MenuConfiguration, User
from .security import current_user

router = APIRouter(prefix="/api/menu-settings", tags=["menu-settings"])


class MenuItemSetting(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    label: str | None = Field(default=None, min_length=1, max_length=60)
    path: str = Field(min_length=1, max_length=100, pattern=r"^/[a-z0-9-]+$")
    hidden: bool = False


class MenuGroupSetting(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    label: str = Field(min_length=1, max_length=40)
    items: list[MenuItemSetting] = Field(max_length=100)


class MenuSettingsUpdate(BaseModel):
    groups: list[MenuGroupSetting] = Field(max_length=20)
    version: int = Field(ge=0)

    @model_validator(mode="after")
    def validate_unique(self):
        labels = [group.label for group in self.groups]
        paths = [item.path for group in self.groups for item in group.items]
        if len(labels) != len(set(labels)) or len(paths) != len(set(paths)):
            raise ValueError("菜单分组和菜单不能重复")
        if any(item.path == "/menu-settings" and item.hidden for group in self.groups for item in group.items):
            raise ValueError("菜单设置入口必须保留显示")
        return self


@router.get("")
def get_settings(db: Session = Depends(get_db), _: User = Depends(current_user)):
    settings = db.get(MenuConfiguration, 1)
    return {"groups": settings.groups if settings else [], "version": settings.version if settings else 0}


@router.put("")
def save_settings(payload: MenuSettingsUpdate, db: Session = Depends(get_db), user: User = Depends(current_user)):
    if not user.is_superadmin:
        raise HTTPException(403, "仅超级管理员可以修改菜单设置")
    groups = [group.model_dump(exclude_none=True) for group in payload.groups]
    if payload.version == 0:
        db.add(MenuConfiguration(id=1, groups=groups, version=1, updated_by=user.id))
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            raise HTTPException(409, "菜单设置已被修改，请重新加载后再保存")
    else:
        result = db.execute(update(MenuConfiguration).where(
            MenuConfiguration.id == 1, MenuConfiguration.version == payload.version
        ).values(groups=groups, version=payload.version + 1, updated_by=user.id))
        if result.rowcount != 1:
            db.rollback()
            raise HTTPException(409, "菜单设置已被修改，请重新加载后再保存")
        db.commit()
    return {"groups": groups, "version": payload.version + 1}
