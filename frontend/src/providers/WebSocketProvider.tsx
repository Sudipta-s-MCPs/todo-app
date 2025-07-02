import { useEffect, type ReactNode } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { useSnackbar } from 'notistack';
import { useAuthStore } from '../store/authStore';
import { websocketService, type WebSocketMessage } from '../services/websocketService';

interface WebSocketProviderProps {
  children: ReactNode;
}

export default function WebSocketProvider({ children }: WebSocketProviderProps) {
  const queryClient = useQueryClient();
  const { enqueueSnackbar } = useSnackbar();
  const token = useAuthStore((state) => state.accessToken);
  const user = useAuthStore((state) => state.user);

  useEffect(() => {
    if (!token) return;

    // Connect to WebSocket
    websocketService.connect(token);

    // Subscribe to events
    const unsubscribers: Array<() => void> = [];

    // Task events
    unsubscribers.push(
      websocketService.subscribe('task_created', (message: WebSocketMessage) => {
        queryClient.invalidateQueries({ queryKey: ['tasks'] });
        queryClient.invalidateQueries({ queryKey: ['stats'] });
        
        if (message.user_id !== user?.id) {
          enqueueSnackbar('New task created', { variant: 'info' });
        }
      })
    );

    unsubscribers.push(
      websocketService.subscribe('task_updated', (message: WebSocketMessage) => {
        queryClient.invalidateQueries({ queryKey: ['tasks'] });
        queryClient.invalidateQueries({ queryKey: ['stats'] });
        
        if (message.user_id !== user?.id) {
          enqueueSnackbar('Task updated', { variant: 'info' });
        }
      })
    );

    unsubscribers.push(
      websocketService.subscribe('task_deleted', (message: WebSocketMessage) => {
        queryClient.invalidateQueries({ queryKey: ['tasks'] });
        queryClient.invalidateQueries({ queryKey: ['stats'] });
        
        if (message.user_id !== user?.id) {
          enqueueSnackbar('Task deleted', { variant: 'info' });
        }
      })
    );

    // Workspace events
    unsubscribers.push(
      websocketService.subscribe('workspace_created', (message: WebSocketMessage) => {
        queryClient.invalidateQueries({ queryKey: ['workspaces'] });
        queryClient.invalidateQueries({ queryKey: ['stats'] });
        
        if (message.user_id !== user?.id) {
          enqueueSnackbar('New workspace created', { variant: 'info' });
        }
      })
    );

    unsubscribers.push(
      websocketService.subscribe('workspace_updated', (message: WebSocketMessage) => {
        queryClient.invalidateQueries({ queryKey: ['workspaces'] });
        
        if (message.user_id !== user?.id) {
          enqueueSnackbar('Workspace updated', { variant: 'info' });
        }
      })
    );

    unsubscribers.push(
      websocketService.subscribe('workspace_deleted', (message: WebSocketMessage) => {
        queryClient.invalidateQueries({ queryKey: ['workspaces'] });
        queryClient.invalidateQueries({ queryKey: ['stats'] });
        queryClient.invalidateQueries({ queryKey: ['tasks'] });
        
        if (message.user_id !== user?.id) {
          enqueueSnackbar('Workspace deleted', { variant: 'warning' });
        }
      })
    );

    // Workspace member events
    unsubscribers.push(
      websocketService.subscribe('workspace_member_added', (message: WebSocketMessage) => {
        queryClient.invalidateQueries({ queryKey: ['workspace-members', message.workspace_id] });
        queryClient.invalidateQueries({ queryKey: ['workspaces'] });
        
        if (message.data.user_id === user?.id) {
          enqueueSnackbar(`You were added to workspace: ${message.data.workspace_name}`, { 
            variant: 'success' 
          });
        }
      })
    );

    unsubscribers.push(
      websocketService.subscribe('workspace_member_removed', (message: WebSocketMessage) => {
        queryClient.invalidateQueries({ queryKey: ['workspace-members', message.workspace_id] });
        queryClient.invalidateQueries({ queryKey: ['workspaces'] });
        
        if (message.data.user_id === user?.id) {
          enqueueSnackbar(`You were removed from workspace: ${message.data.workspace_name}`, { 
            variant: 'warning' 
          });
          // If user is currently viewing this workspace, redirect to dashboard
          if (window.location.pathname.includes(message.workspace_id!)) {
            window.location.href = '/dashboard';
          }
        }
      })
    );

    unsubscribers.push(
      websocketService.subscribe('workspace_member_updated', (message: WebSocketMessage) => {
        queryClient.invalidateQueries({ queryKey: ['workspace-members', message.workspace_id] });
        
        if (message.data.user_id === user?.id) {
          enqueueSnackbar(`Your role was updated to ${message.data.role}`, { 
            variant: 'info' 
          });
        }
      })
    );

    // Cleanup
    return () => {
      unsubscribers.forEach(unsubscribe => unsubscribe());
      websocketService.disconnect();
    };
  }, [token, user?.id, queryClient, enqueueSnackbar]);

  return <>{children}</>;
}