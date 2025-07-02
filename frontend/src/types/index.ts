// API Response Types
export interface ApiResponse<T> {
  data?: T;
  error?: string;
  message?: string;
}

// User Types
export interface User {
  id: string;
  email: string;
  name: string;
  avatar_url?: string;
  timezone: string;
  locale: string;
  is_active: boolean;
  is_verified: boolean;
  two_factor_enabled: boolean;
  created_at: string;
  last_active_at?: string;
  is_admin: boolean;
}

// Auth Types
export interface LoginCredentials {
  email: string;
  password: string;
}

export interface RegisterCredentials {
  email: string;
  password: string;
  name: string;
  timezone?: string;
  locale?: string;
}

export interface AuthResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
  user: User;
}

// Workspace Types
export interface Workspace {
  id: string;
  name: string;
  type: 'personal' | 'shared';
  owner_id: string;
  description?: string;
  emoji?: string;
  color?: string;
  created_at: string;
  updated_at: string;
  member_count?: number;
  task_count?: number;
}

// List Types
export interface List {
  id: string;
  workspace_id: string;
  name: string;
  type: 'default' | 'smart' | 'custom';
  is_default: boolean;
  icon?: string;
  color: string;
  position: number;
  settings_json: Record<string, any>;
  created_at: string;
  updated_at: string;
  is_archived: boolean;
  task_count?: number;
}

export interface ListCreate {
  name: string;
  type?: 'default' | 'smart' | 'custom';
  icon?: string;
  color?: string;
  position?: number;
  settings?: Record<string, any>;
}

export interface ListUpdate {
  name?: string;
  icon?: string;
  color?: string;
  position?: number;
  settings?: Record<string, any>;
}

// Task Types
export interface Task {
  id: string;
  list_id: string;
  title: string;
  description?: string;
  priority: 'low' | 'medium' | 'high';
  status: 'todo' | 'in_progress' | 'completed' | 'archived';
  due_date?: string;
  completed_at?: string;
  parent_task_id?: string;
  position: number;
  task_metadata?: Record<string, any>;
  created_by: string;
  created_via_device_id?: string;
  created_via_method: string;
  created_via_session_id?: string;
  created_at: string;
  updated_at: string;
  // Additional fields populated by API
  creator_name?: string;
  assigned_users?: Array<{id: string; name: string; email: string}>;
  subtask_count?: number;
  comment_count?: number;
  attachment_count?: number;
  // Frontend-only fields
  tags?: string[];
  reminder_date?: string;
  workspace?: Workspace;
  workspace_id?: string;
}

export interface TaskAttachment {
  id: string;
  task_id: string;
  filename: string;
  file_size: number;
  mime_type: string;
  storage_path: string;
  storage_etag?: string;
  storage_version_id?: string;
  uploaded_by: string;
  uploaded_at: string;
  download_url?: string;
  uploader_name?: string;
}

export interface TaskComment {
  id: string;
  task_id: string;
  content: string;
  created_by: string;
  created_at: string;
  updated_at: string;
  author?: User;
}

// Activity Types
export interface Activity {
  id: string;
  user_id: string;
  action: string;
  resource_type: string;
  resource_id: string;
  details: Record<string, any>;
  device_info?: DeviceInfo;
  created_at: string;
}

export interface DeviceInfo {
  device_id: string;
  device_name?: string;
  device_type: 'web' | 'mobile' | 'desktop' | 'tablet' | 'api';
  os?: string;
  browser?: string;
}

// User device from auth endpoints
export interface UserDevice {
  id: string;
  device_name: string;
  device_type: 'web' | 'mobile' | 'desktop' | 'tablet' | 'api';
  device_identifier: string;
  is_trusted: boolean;
  is_active: boolean;
  last_used_at: string;
  created_at: string;
  is_current?: boolean;
}

// Filter and Sort Types
export interface TaskFilter {
  workspace_id?: string;
  list_id?: string;
  status?: Task['status'];
  priority?: Task['priority'];
  assigned_to?: string;
  tags?: string[];
  search?: string;
  due_date_from?: string;
  due_date_to?: string;
}

export interface SortOptions {
  field: 'created_at' | 'updated_at' | 'due_date' | 'priority' | 'title';
  order: 'asc' | 'desc';
}

// Chat Types
export interface ChatMessage {
  id: string;
  content: string;
  sender: 'user' | 'assistant';
  timestamp: string;
  metadata?: {
    type?: 'welcome' | 'error' | 'success' | 'task';
    usedAI?: boolean;
    confidence?: number;
    tasks?: Task[];
    action?: string;
  };
}

export interface ChatConversation {
  id: string;
  title?: string;
  created_at: string;
  updated_at: string;
  message_count: number;
}

export interface ChatResponse {
  message: ChatMessage;
  conversationId?: string;
  tasks?: Task[];
  action?: string;
  usedAI: boolean;
}

// WebSocket Types
export interface WebSocketMessage {
  type: 'task_created' | 'task_updated' | 'task_deleted' | 'list_updated' | 'workspace_updated';
  resource_id: string;
  data: any;
  timestamp: string;
}

// API Request Types
export interface TaskCreate {
  title: string;
  description?: string;
  workspace_id: string;
  priority?: 'low' | 'medium' | 'high';
  status?: 'todo' | 'in_progress' | 'completed' | 'archived';
  due_date?: string;
  reminder_date?: string;
  tags?: string[];
  parent_id?: string;
}

export interface TaskUpdate {
  title?: string;
  description?: string;
  priority?: 'low' | 'medium' | 'high';
  status?: 'todo' | 'in_progress' | 'completed' | 'archived';
  due_date?: string;
  reminder_date?: string;
  tags?: string[];
}

// AI Analysis Types
export interface AIAnalysis {
  suggested_action: 'create_new' | 'update_existing' | 'merge';
  reasoning: string;
  confidence: number;
  suggested_title?: string;
}

export interface DuplicateTaskError {
  detail: string;
  duplicates: Task[];
  similarity_scores: Record<string, {
    title_similarity: number;
    description_similarity: number;
    combined_similarity: number;
    ai_confidence?: number;
    ai_reasoning?: string;
  }>;
  ai_analysis?: AIAnalysis;
}

export interface WorkspaceCreate {
  name: string;
  description?: string;
  type?: 'personal' | 'shared';
  emoji?: string;
  color?: string;
}

export interface WorkspaceUpdate {
  name?: string;
  description?: string;
  emoji?: string;
  color?: string;
}

export interface WorkspaceMember {
  id: string;
  workspace_id: string;
  user_id: string;
  role: 'viewer' | 'member' | 'admin';
  joined_at: string;
  user?: User;
}

// List Response Types
export interface TasksResponse {
  tasks: Task[];
  total: number;
  skip: number;
  limit: number;
}

export type WorkspacesResponse = Workspace[];