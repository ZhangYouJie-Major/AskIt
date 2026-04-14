import api from './index'

export interface Department {
  id: number
  name: string
  description: string | null
  is_active: boolean
  user_count: number
}

export interface CreateDepartmentRequest {
  name: string
  description?: string
}

export interface UpdateDepartmentRequest {
  name: string
  description?: string
}

export interface UpdateDepartmentStatusRequest {
  is_active: boolean
}

export const departmentsApi = {
  /**
   * 获取部门列表
   */
  list: (): Promise<Department[]> => {
    return api.get('/departments/')
  },

  /**
   * 创建部门
   */
  create: (data: CreateDepartmentRequest): Promise<Department> => {
    return api.post('/departments', data)
  },

  /**
   * 更新部门
   */
  update: (id: number, data: UpdateDepartmentRequest): Promise<Department> => {
    return api.put(`/departments/${id}`, data)
  },

  /**
   * 更新部门状态
   */
  updateStatus: (id: number, data: UpdateDepartmentStatusRequest): Promise<Department> => {
    return api.put(`/departments/${id}/status`, data)
  }
}
