import { invoke } from '@tauri-apps/api/core';
import { listen } from '@tauri-apps/api/event';

interface ServerInfo {
  url: string;
  port: number;
  status: string;
}

class WebWhisperWebView {
  private loadingScreen: HTMLElement;
  private errorScreen: HTMLElement;
  private statusText: HTMLElement;
  private gradioFrame: HTMLIFrameElement;
  private retryCount = 0;
  private maxRetries = 5;

  constructor() {
    this.loadingScreen = document.getElementById('loading-screen')!;
    this.errorScreen = document.getElementById('error-screen')!;
    this.statusText = document.getElementById('status-text')!;
    this.gradioFrame = document.getElementById('gradio-frame') as HTMLIFrameElement;
    
    this.initializeWebView();
  }

  private async initializeWebView() {
    try {
      this.updateStatus('Pythonサーバーを起動中...');
      await this.startGradioServer();
      
      this.updateStatus('サーバーへの接続を確認中...');
      const serverInfo = await this.waitForServer();
      
      this.updateStatus('Web Whisperを読み込み中...');
      await this.loadGradioInterface(serverInfo.url);
      
    } catch (error) {
      console.error('Initialization error:', error);
      this.showError(error as string);
    }
  }

  private async startGradioServer(): Promise<void> {
    try {
      // Start the Gradio server via Tauri command
      await invoke('start_gradio_server');
    } catch (error) {
      console.error('Failed to start Gradio server:', error);
      throw `サーバーの起動に失敗しました: ${error}`;
    }
  }

  private async waitForServer(): Promise<ServerInfo> {
    const maxWaitTime = 30000; // 30 seconds
    const checkInterval = 1000; // 1 second
    const startTime = Date.now();

    return new Promise(async (resolve, reject) => {
      const checkServer = async () => {
        try {
          const serverInfo = await invoke<ServerInfo>('get_server_info');
          
          if (serverInfo.status === 'running') {
            // Test if the server is actually responding
            try {
              const response = await fetch(serverInfo.url);
              if (response.ok) {
                resolve(serverInfo);
                return;
              }
            } catch (fetchError) {
              console.log('Server not ready yet:', fetchError);
            }
          }
          
          // Continue waiting if within time limit
          if (Date.now() - startTime < maxWaitTime) {
            setTimeout(checkServer, checkInterval);
          } else {
            reject('サーバーの起動がタイムアウトしました');
          }
        } catch (error) {
          console.error('Error checking server:', error);
          if (Date.now() - startTime < maxWaitTime) {
            setTimeout(checkServer, checkInterval);
          } else {
            reject(`サーバーの確認に失敗しました: ${error}`);
          }
        }
      };
      
      checkServer();
    });
  }

  private async loadGradioInterface(url: string): Promise<void> {
    return new Promise((resolve, reject) => {
      // Set up frame load handlers
      this.gradioFrame.onload = () => {
        // Wait a bit for Gradio to fully initialize
        setTimeout(() => {
          this.showGradioInterface();
          resolve();
        }, 1000);
      };

      this.gradioFrame.onerror = () => {
        reject('Gradioインターフェースの読み込みに失敗しました');
      };

      // Load the Gradio interface
      this.gradioFrame.src = url;
      
      // Fallback timeout
      setTimeout(() => {
        if (this.gradioFrame.style.display === 'none') {
          reject('Gradioの読み込みがタイムアウトしました');
        }
      }, 15000);
    });
  }

  private showGradioInterface() {
    this.loadingScreen.style.display = 'none';
    this.errorScreen.style.display = 'none';
    this.gradioFrame.style.display = 'block';
  }

  private showError(message: string) {
    this.loadingScreen.style.display = 'none';
    this.gradioFrame.style.display = 'none';
    
    const errorMessage = this.errorScreen.querySelector('p')!;
    errorMessage.textContent = message;
    this.errorScreen.style.display = 'block';
  }

  private updateStatus(message: string) {
    this.statusText.textContent = message;
  }
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
  new WebWhisperWebView();
});