// Common shared types for the application
// Individual domain types live in ./src/types/{domain}.ts

// API response wrapper
export interface ApiResponse<T = unknown> {
  code: number
  message: string
  data: T
}

// Pagination
export interface PaginationParams {
  page: number
  page_size: number
}

export interface PaginatedData<T> {
  items: T[]
  total: number
  page: number
  page_size: number
}
