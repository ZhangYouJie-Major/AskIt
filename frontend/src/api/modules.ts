import api from './index'

export interface QueryRequest {
  question: string
  department_id: number
  history?: Array<{ role: string; content: string }>
  top_k?: number
}

export interface QueryResponse {
  answer: string
  sources: Array<{
    document_id: number
    chunk_id: string
    filename: string
    score: number
  }>
}

export const queryApi = {
  /**
   * 执行 RAG 查询
   */
  query: (data: QueryRequest) => {
    return api.post<any, QueryResponse>('/query/', data)
  }
}

export interface Document {
  id: number
  filename: string
  original_filename: string
  file_type: string
  file_size: number
  status: string
  vectorized: boolean
  chunk_count: number
}

export interface DocumentListResponse {
  total: number
  documents: Document[]
}

export const documentApi = {
  /**
   * 获取文档列表
   */
  list: (params?: { department_id?: number; skip?: number; limit?: number }) => {
    return api.get<any, DocumentListResponse>('/documents/', { params })
  },

  /**
   * 上传文档
   */
  upload: (file: File, department_id: number) => {
    const formData = new FormData()
    formData.append('file', file)
    formData.append('department_id', department_id.toString())
    return api.post<any, Document>('/documents/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
  },

  /**
   * 删除文档
   */
  delete: (document_id: number) => {
    return api.delete(`/documents/${document_id}`)
  }
}
