import api from './index'

export interface LoginForm {
  username: string
  password: string
}

export interface RegisterForm {
  username: string
  email: string
  password: string
  full_name?: string
  department_id?: number
}

export interface UserInfo {
  id: number
  username: string
  email: string
  full_name: string | null
  department_id: number | null
  department_name: string | null
  is_superuser: boolean
}

export interface LoginResponse {
  access_token: string
  token_type: string
  expires_in: number
  user: UserInfo
}

export const authApi = {
  // 登录
  login: (data: LoginForm): Promise<LoginResponse> => {
    return api.post('/auth/login/json', data)
  },

  // 注册
  register: (data: RegisterForm): Promise<UserInfo> => {
    return api.post('/auth/register', data)
  },

  // 获取当前用户信息
  getMe: (): Promise<UserInfo> => {
    return api.get('/auth/me')
  }
}

// 本地存储工具
export const authStorage = {
  getToken: () => {
    const token = localStorage.getItem('access_token')
    console.log('[Auth] getToken:', !!token)
    return token
  },
  setToken: (token: string) => {
    console.log('[Auth] setToken:', !!token)
    localStorage.setItem('access_token', token)
  },
  removeToken: () => localStorage.removeItem('access_token'),

  getUser: (): UserInfo | null => {
    const user = localStorage.getItem('user_info')
    console.log('[Auth] getUser:', !!user)
    return user ? JSON.parse(user) : null
  },
  setUser: (user: UserInfo) => {
    console.log('[Auth] setUser:', user.username)
    localStorage.setItem('user_info', JSON.stringify(user))
  },
  removeUser: () => localStorage.removeItem('user_info'),

  clear: () => {
    console.log('[Auth] clear')
    localStorage.removeItem('access_token')
    localStorage.removeItem('user_info')
  }
}
