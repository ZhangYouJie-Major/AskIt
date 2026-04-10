"""
RBAC 业务逻辑服务
"""
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from sqlalchemy.orm import selectinload

from app.models.rbac import Permission, Role, RolePermission, UserRole


# 预定义的9个权限
PERMISSIONS_DATA = [
    {"code": "user:read", "name": "查看用户", "description": "允许查看用户信息"},
    {"code": "user:write", "name": "创建/编辑用户", "description": "允许创建和编辑用户"},
    {"code": "user:delete", "name": "删除用户", "description": "允许删除用户"},
    {"code": "document:read", "name": "查看文档", "description": "允许查看文档"},
    {"code": "document:write", "name": "上传/编辑文档", "description": "允许上传和编辑文档"},
    {"code": "document:delete", "name": "删除文档", "description": "允许删除文档"},
    {"code": "query:execute", "name": "发起问答", "description": "允许发起问答查询"},
    {"code": "settings:read", "name": "查看配置", "description": "允许查看系统配置"},
    {"code": "settings:write", "name": "修改配置", "description": "允许修改系统配置"},
]


class RBACService:
    """RBAC 业务逻辑服务"""

    @staticmethod
    async def init_permissions(db: AsyncSession) -> List[Permission]:
        """初始化权限数据（仅在不存在时）"""
        result = await db.execute(select(Permission))
        existing = result.scalars().all()

        if len(existing) == 0:
            # 创建所有权限
            permissions = [
                Permission(**p) for p in PERMISSIONS_DATA
            ]
            db.add_all(permissions)
            await db.commit()
            return permissions

        return list(existing)

    @staticmethod
    async def get_all_permissions(db: AsyncSession) -> List[Permission]:
        """获取所有权限"""
        result = await db.execute(select(Permission).order_by(Permission.id))
        return list(result.scalars().all())

    @staticmethod
    async def get_all_roles(db: AsyncSession, include_inactive: bool = False) -> List[Role]:
        """获取所有角色"""
        query = select(Role).options(selectinload(Role.permissions))
        if not include_inactive:
            query = query.where(Role.is_active == True)
        result = await db.execute(query.order_by(Role.id))
        return list(result.scalars().all())

    @staticmethod
    async def get_role_by_id(db: AsyncSession, role_id: int) -> Optional[Role]:
        """根据ID获取角色"""
        result = await db.execute(
            select(Role)
            .options(selectinload(Role.permissions))
            .where(Role.id == role_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def create_role(
        db: AsyncSession,
        name: str,
        description: Optional[str] = None,
        permission_ids: Optional[List[int]] = None
    ) -> Role:
        """创建角色"""
        role = Role(name=name, description=description, is_active=True)
        db.add(role)
        await db.flush()

        if permission_ids:
            for perm_id in permission_ids:
                rp = RolePermission(role_id=role.id, permission_id=perm_id)
                db.add(rp)

        await db.commit()
        await db.refresh(role)
        return role

    @staticmethod
    async def update_role(
        db: AsyncSession,
        role_id: int,
        name: Optional[str] = None,
        description: Optional[str] = None,
        is_active: Optional[bool] = None
    ) -> Optional[Role]:
        """更新角色"""
        role = await RBACService.get_role_by_id(db, role_id)
        if not role:
            return None

        if name is not None:
            role.name = name
        if description is not None:
            role.description = description
        if is_active is not None:
            role.is_active = is_active

        await db.commit()
        await db.refresh(role)
        return role

    @staticmethod
    async def update_role_permissions(
        db: AsyncSession,
        role_id: int,
        permission_ids: List[int]
    ) -> Optional[Role]:
        """更新角色权限"""
        role = await RBACService.get_role_by_id(db, role_id)
        if not role:
            return None

        # 删除旧关联
        await db.execute(
            delete(RolePermission).where(RolePermission.role_id == role_id)
        )

        # 添加新关联
        for perm_id in permission_ids:
            rp = RolePermission(role_id=role_id, permission_id=perm_id)
            db.add(rp)

        await db.commit()
        await db.refresh(role)
        return role

    @staticmethod
    async def delete_role(db: AsyncSession, role_id: int) -> bool:
        """删除角色（同时删除关联）"""
        role = await RBACService.get_role_by_id(db, role_id)
        if not role:
            return False

        # 删除关联（级联自动处理，但显式删除更干净）
        await db.execute(
            delete(RolePermission).where(RolePermission.role_id == role_id)
        )
        await db.execute(
            delete(UserRole).where(UserRole.role_id == role_id)
        )

        await db.delete(role)
        await db.commit()
        return True

    @staticmethod
    async def get_user_roles(db: AsyncSession, user_id: int) -> List[Role]:
        """获取用户的所有角色"""
        result = await db.execute(
            select(Role)
            .join(UserRole, Role.id == UserRole.role_id)
            .where(UserRole.user_id == user_id)
        )
        return list(result.scalars().all())

    @staticmethod
    async def assign_roles_to_user(
        db: AsyncSession,
        user_id: int,
        role_ids: List[int]
    ) -> List[UserRole]:
        """为用户分配角色（批量替换）"""
        # 先删除用户的所有旧角色关联
        await db.execute(
            delete(UserRole).where(UserRole.user_id == user_id)
        )

        # 添加新角色关联
        created = []
        for role_id in role_ids:
            ur = UserRole(user_id=user_id, role_id=role_id)
            db.add(ur)
            created.append(ur)

        await db.commit()
        return created

    @staticmethod
    async def remove_role_from_user(
        db: AsyncSession,
        user_id: int,
        role_id: int
    ) -> bool:
        """移除用户角色"""
        result = await db.execute(
            delete(UserRole).where(
                UserRole.user_id == user_id,
                UserRole.role_id == role_id
            )
        )
        await db.commit()
        return result.rowcount > 0

    @staticmethod
    async def get_role_usage_count(db: AsyncSession, role_id: int) -> int:
        """获取角色被使用的数量"""
        result = await db.execute(
            select(UserRole).where(UserRole.role_id == role_id)
        )
        return len(result.scalars().all())
