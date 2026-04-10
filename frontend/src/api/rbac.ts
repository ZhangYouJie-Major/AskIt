// frontend/src/api/rbac.ts
import api from './index'

// ============ Types ============

export interface Permission {
  id: number
  code: string
  name: string
  description: string
}

export interface Role {
  id: number
  name: string
  description: string | null
  is_active: boolean
  permissions: Permission[]
}

export interface RoleBrief {
  id: number
  name: string
  description: string | null
  is_active: boolean
  permission_count: number
  user_count: number
}

export interface UserRole {
  id: number
  name: string
  description: string | null
}

export interface CreateRoleRequest {
  name: string
  description?: string
  permission_ids: number[]
}

export interface UpdateRoleRequest {
  name?: string
  description?: string
  is_active?: boolean
}

export interface UpdateRolePermissionsRequest {
  permission_ids: number[]
}

export interface AssignRolesRequest {
  role_ids: number[]
}

// ============ Permissions API ============

export const permissionsApi = {
  /**
   * 获取所有权限列表
   */
  list: () => {
    return api.get<any, Permission[]>('/permissions/')
  }
}

// ============ Roles API ============

export const rolesApi = {
  /**
   * 获取角色列表
   */
  list: () => {
    return api.get<any, RoleBrief[]>('/roles/')
  },

  /**
   * 获取角色详情（含权限）
   */
  getById: (id: number) => {
    return api.get<any, Role>(`/roles/${id}`)
  },

  /**
   * 创建角色
   */
  create: (data: CreateRoleRequest) => {
    return api.post<any, Role>('/roles/', data)
  },

  /**
   * 更新角色
   */
  update: (id: number, data: UpdateRoleRequest) => {
    return api.put<any, Role>(`/roles/${id}`, data)
  },

  /**
   * 更新角色权限
   */
  updatePermissions: (id: number, data: UpdateRolePermissionsRequest) => {
    return api.put<any, Role>(`/roles/${id}/permissions`, data)
  },

  /**
   * 删除角色
   */
  delete: (id: number) => {
    return api.delete(`/roles/${id}`)
  }
}

// ============ User Roles API ============

export const userRolesApi = {
  /**
   * 获取用户角色
   */
  getUserRoles: (userId: number) => {
    return api.get<any, UserRole[]>(`/users/${userId}/roles`)
  },

  /**
   * 为用户分配角色
   */
  assign: (userId: number, data: AssignRolesRequest) => {
    return api.post<any, any>(`/users/${userId}/roles`, data)
  },

  /**
   * 移除用户角色
   */
  remove: (userId: number, roleId: number) => {
    return api.delete(`/users/${userId}/roles/${roleId}`)
  }
}