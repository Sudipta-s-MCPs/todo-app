import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ThemeProvider, CssBaseline } from '@mui/material';
import { SnackbarProvider } from 'notistack';
import { LocalizationProvider } from '@mui/x-date-pickers';
import { AdapterDateFns } from '@mui/x-date-pickers/AdapterDateFns';

import { theme } from './utils/theme';

// Pages
import Login from './pages/Login';
import Register from './pages/Register';
import Dashboard from './pages/Dashboard';
import Tasks from './pages/Tasks';
import Workspaces from './pages/Workspaces';
import Lists from './pages/Lists';
import Profile from './pages/Profile';
import ChatAgent from './pages/ChatAgent';

// Components
import Layout from './components/Layout';
import PrivateRoute from './components/PrivateRoute';
import PWAInstallPrompt from './components/PWAInstallPrompt';

// Providers
import WebSocketProvider from './providers/WebSocketProvider';

// Create a query client
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5 * 60 * 1000, // 5 minutes
      retry: 1,
    },
  },
});

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <ThemeProvider theme={theme}>
        <LocalizationProvider dateAdapter={AdapterDateFns}>
          <SnackbarProvider 
            maxSnack={3} 
            anchorOrigin={{ vertical: 'bottom', horizontal: 'left' }}
          >
            <CssBaseline />
            <Router>
              <Routes>
                {/* Public Routes */}
                <Route path="/login" element={<Login />} />
                <Route path="/register" element={<Register />} />
                
                {/* Private Routes */}
                <Route element={<PrivateRoute />}>
                  <Route element={
                    <WebSocketProvider>
                      <Layout />
                    </WebSocketProvider>
                  }>
                    <Route path="/" element={<Navigate to="/dashboard" replace />} />
                    <Route path="/dashboard" element={<Dashboard />} />
                    <Route path="/tasks" element={<Tasks />} />
                    <Route path="/workspaces" element={<Workspaces />} />
                    <Route path="/workspaces/:workspaceId/lists" element={<Lists />} />
                    <Route path="/workspaces/:workspaceId/lists/:listId/tasks" element={<Tasks />} />
                    <Route path="/profile" element={<Profile />} />
                    <Route path="/chat" element={<ChatAgent />} />
                    <Route path="/settings" element={<Navigate to="/profile" replace />} />
                  </Route>
                </Route>
                
                {/* 404 */}
                <Route path="*" element={<Navigate to="/" replace />} />
              </Routes>
            </Router>
            <PWAInstallPrompt />
          </SnackbarProvider>
        </LocalizationProvider>
      </ThemeProvider>
    </QueryClientProvider>
  );
}

export default App;
