/**
 * Device ID Management for Smart-ToDo PWA
 * Handles persistent device identification across sessions
 */

import { openDB } from 'idb';
import type { IDBPDatabase } from 'idb';

const DB_NAME = 'SmartTodoDevice';
const DB_VERSION = 1;
const STORE_NAME = 'device';
const DEVICE_ID_KEY = 'deviceId';

interface DeviceInfo {
  deviceId: string;
  deviceName: string;
  deviceType: 'web' | 'pwa';
  createdAt: string;
  fingerprint: string;
}

/**
 * Get browser/device name for display
 */
function getDeviceName(): string {
  const userAgent = navigator.userAgent;
  const platform = navigator.platform || 'Unknown Platform';
  
  // Detect browser
  let browser = 'Unknown Browser';
  if (userAgent.includes('Chrome')) browser = 'Chrome';
  else if (userAgent.includes('Firefox')) browser = 'Firefox';
  else if (userAgent.includes('Safari')) browser = 'Safari';
  else if (userAgent.includes('Edge')) browser = 'Edge';
  else if (userAgent.includes('Opera')) browser = 'Opera';
  
  // Detect OS
  let os = platform;
  if (userAgent.includes('Windows')) os = 'Windows';
  else if (userAgent.includes('Mac')) os = 'macOS';
  else if (userAgent.includes('Linux')) os = 'Linux';
  else if (userAgent.includes('Android')) os = 'Android';
  else if (userAgent.includes('iOS') || userAgent.includes('iPhone') || userAgent.includes('iPad')) os = 'iOS';
  
  return `${browser} on ${os}`;
}

/**
 * Check if running as installed PWA
 */
function isPWA(): boolean {
  return window.matchMedia('(display-mode: standalone)').matches ||
         window.matchMedia('(display-mode: fullscreen)').matches ||
         (window.navigator as any).standalone === true;
}

/**
 * Generate a simple fingerprint based on browser characteristics
 */
async function generateFingerprint(): Promise<string> {
  const canvas = document.createElement('canvas');
  const ctx = canvas.getContext('2d');
  
  if (!ctx) {
    return 'no-canvas';
  }
  
  // Canvas fingerprinting
  ctx.textBaseline = 'top';
  ctx.font = '14px Arial';
  ctx.textBaseline = 'alphabetic';
  ctx.fillStyle = '#f60';
  ctx.fillRect(125, 1, 62, 20);
  ctx.fillStyle = '#069';
  ctx.fillText('Smart-ToDo PWA', 2, 15);
  ctx.fillStyle = 'rgba(102, 204, 0, 0.7)';
  ctx.fillText('Device ID', 4, 17);
  
  const canvasData = canvas.toDataURL();
  
  // Combine with other browser properties
  const fingerprint = {
    canvas: canvasData.substring(0, 100), // Use part of canvas data
    screen: `${screen.width}x${screen.height}x${screen.colorDepth}`,
    timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
    language: navigator.language,
    platform: navigator.platform,
    cores: navigator.hardwareConcurrency || 0,
  };
  
  // Create a simple hash
  const str = JSON.stringify(fingerprint);
  let hash = 0;
  for (let i = 0; i < str.length; i++) {
    const char = str.charCodeAt(i);
    hash = ((hash << 5) - hash) + char;
    hash = hash & hash; // Convert to 32-bit integer
  }
  
  return Math.abs(hash).toString(36);
}

/**
 * Generate a UUID v4
 */
function generateUUID(): string {
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
    const r = Math.random() * 16 | 0;
    const v = c === 'x' ? r : (r & 0x3 | 0x8);
    return v.toString(16);
  });
}

/**
 * Open IndexedDB connection
 */
async function openDeviceDB(): Promise<IDBPDatabase> {
  return openDB(DB_NAME, DB_VERSION, {
    upgrade(db) {
      if (!db.objectStoreNames.contains(STORE_NAME)) {
        db.createObjectStore(STORE_NAME);
      }
    },
  });
}

/**
 * Get or create device info
 */
export async function getDeviceInfo(): Promise<DeviceInfo> {
  try {
    // Request persistent storage
    if ('storage' in navigator && 'persist' in navigator.storage) {
      const isPersisted = await navigator.storage.persist();
      console.log(`Persistent storage ${isPersisted ? 'granted' : 'not granted'}`);
    }
    
    const db = await openDeviceDB();
    
    // Try to get existing device info
    const existingDevice = await db.get(STORE_NAME, DEVICE_ID_KEY) as DeviceInfo | undefined;
    
    if (existingDevice) {
      console.log('Using existing device ID:', existingDevice.deviceId);
      return existingDevice;
    }
    
    // Generate new device info
    console.log('Generating new device ID...');
    const fingerprint = await generateFingerprint();
    const deviceInfo: DeviceInfo = {
      deviceId: `${fingerprint}-${generateUUID()}`,
      deviceName: getDeviceName(),
      deviceType: isPWA() ? 'pwa' : 'web',
      createdAt: new Date().toISOString(),
      fingerprint,
    };
    
    // Store in IndexedDB
    await db.put(STORE_NAME, deviceInfo, DEVICE_ID_KEY);
    console.log('New device ID created:', deviceInfo.deviceId);
    
    return deviceInfo;
  } catch (error) {
    console.error('Error managing device ID:', error);
    
    // Fallback to session-based ID if IndexedDB fails
    const sessionId = sessionStorage.getItem('fallbackDeviceId') || generateUUID();
    sessionStorage.setItem('fallbackDeviceId', sessionId);
    
    return {
      deviceId: sessionId,
      deviceName: getDeviceName(),
      deviceType: isPWA() ? 'pwa' : 'web',
      createdAt: new Date().toISOString(),
      fingerprint: 'fallback',
    };
  }
}

/**
 * Clear device info (for testing or user request)
 */
export async function clearDeviceInfo(): Promise<void> {
  try {
    const db = await openDeviceDB();
    await db.delete(STORE_NAME, DEVICE_ID_KEY);
    sessionStorage.removeItem('fallbackDeviceId');
    console.log('Device info cleared');
  } catch (error) {
    console.error('Error clearing device info:', error);
  }
}