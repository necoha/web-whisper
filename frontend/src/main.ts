import { invoke } from '@tauri-apps/api/core';
import { listen } from '@tauri-apps/api/event';

interface ServerInfo {
  url: string;
  port: number;
  status: string;
}

class WebWhisperApp {
  private fileInput: HTMLInputElement;
  private dropZone: HTMLDivElement;
  private actionBtn: HTMLButtonElement;
  private btnText: HTMLSpanElement;
  private btnIcon: HTMLSpanElement;
  private statusCard: HTMLDivElement;
  private statusIcon: HTMLDivElement;
  private statusTitle: HTMLDivElement;
  private statusMessage: HTMLDivElement;
  private progressContainer: HTMLDivElement;
  private progressFill: HTMLDivElement;
  private progressText: HTMLDivElement;
  private resultCard: HTMLDivElement;
  private resultContent: HTMLDivElement;
  private errorCard: HTMLDivElement;
  private errorTitle: HTMLDivElement;
  private errorMessage: HTMLDivElement;
  private copyBtn: HTMLButtonElement;
  private saveBtn: HTMLButtonElement;
  private newBtn: HTMLButtonElement;
  private retryBtn: HTMLButtonElement;
  private gpuStatus: HTMLDivElement;
  
  private serverInfo: ServerInfo | null = null;
  private selectedFile: File | null = null;

  constructor() {
    this.initializeElements();
    this.setupEventListeners();
    this.initializeApp();
  }

  private initializeElements() {
    // Get DOM elements
    this.fileInput = document.getElementById('file-input') as HTMLInputElement;
    this.dropZone = document.getElementById('drop-zone') as HTMLDivElement;
    this.actionBtn = document.getElementById('action-btn') as HTMLButtonElement;
    this.btnText = document.getElementById('btn-text') as HTMLSpanElement;
    this.btnIcon = document.getElementById('btn-icon') as HTMLSpanElement;
    
    // Status elements
    this.statusCard = document.getElementById('status-card') as HTMLDivElement;
    this.statusIcon = document.getElementById('status-icon') as HTMLDivElement;
    this.statusTitle = document.getElementById('status-title') as HTMLDivElement;
    this.statusMessage = document.getElementById('status-message') as HTMLDivElement;
    
    // Progress elements
    this.progressContainer = document.getElementById('progress-container') as HTMLDivElement;
    this.progressFill = document.getElementById('progress-fill') as HTMLDivElement;
    this.progressText = document.getElementById('progress-text') as HTMLDivElement;
    
    // Result elements
    this.resultCard = document.getElementById('result-card') as HTMLDivElement;
    this.resultContent = document.getElementById('result-content') as HTMLDivElement;
    this.copyBtn = document.getElementById('copy-btn') as HTMLButtonElement;
    this.saveBtn = document.getElementById('save-btn') as HTMLButtonElement;
    this.newBtn = document.getElementById('new-btn') as HTMLButtonElement;
    
    // Error elements
    this.errorCard = document.getElementById('error-card') as HTMLDivElement;
    this.errorTitle = document.getElementById('error-title') as HTMLDivElement;
    this.errorMessage = document.getElementById('error-message') as HTMLDivElement;
    this.retryBtn = document.getElementById('retry-btn') as HTMLButtonElement;
    
    // GPU info element
    this.gpuStatus = document.getElementById('gpu-status') as HTMLDivElement;
  }

  private setupEventListeners() {
    // File input
    this.dropZone.addEventListener('click', () => this.fileInput.click());
    this.fileInput.addEventListener('change', (e) => this.handleFileSelect(e));

    // Action button
    this.actionBtn.addEventListener('click', () => this.startTranscription());

    // Result actions
    this.copyBtn.addEventListener('click', () => this.copyResult());
    this.saveBtn.addEventListener('click', () => this.saveResult());
    this.newBtn.addEventListener('click', () => this.resetApp());
    this.retryBtn.addEventListener('click', () => this.retryTranscription());

    // Drag and drop
    this.setupDragAndDrop();
  }

  private setupDragAndDrop() {
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
      this.dropZone.addEventListener(eventName, (e) => e.preventDefault());
    });

    this.dropZone.addEventListener('dragover', () => {
      this.dropZone.classList.add('dragover');
    });

    this.dropZone.addEventListener('dragleave', () => {
      this.dropZone.classList.remove('dragover');
    });

    this.dropZone.addEventListener('drop', (e) => {
      e.preventDefault();
      this.dropZone.classList.remove('dragover');
      const files = (e as DragEvent).dataTransfer?.files;
      if (files && files.length > 0) {
        this.handleFile(files[0]);
      }
    });
  }

  private async initializeApp() {
    this.updateStatus('準備完了', 'success', '音声ファイルを選択してください');
    this.hideResults();
    this.hideError();
    await this.loadGpuInfo();
  }

  private handleFileSelect(event: Event) {
    const input = event.target as HTMLInputElement;
    if (input.files && input.files[0]) {
      this.handleFile(input.files[0]);
    }
  }

  private handleFile(file: File) {
    if (!this.isValidAudioFile(file)) {
      this.showError('対応していないファイル形式です', 
        '対応形式: MP3、WAV、M4A、FLAC、MP4、AVI、MOV、MKV');
      return;
    }

    this.selectedFile = file;
    this.updateStatus('ファイル選択完了', 'success', 
      `${file.name} (${this.formatFileSize(file.size)})`);
    
    // Update drop zone
    this.dropZone.querySelector('.drop-icon')!.textContent = '✅';
    this.dropZone.querySelector('.drop-text')!.textContent = file.name;
    this.dropZone.querySelector('.drop-hint')!.textContent = 
      `${this.formatFileSize(file.size)} - 転写する準備ができました`;

    // Enable action button
    this.actionBtn.disabled = false;
    this.btnText.textContent = '転写を開始';
    this.btnIcon.textContent = '🚀';

    this.hideResults();
    this.hideError();
  }

  private isValidAudioFile(file: File): boolean {
    const validTypes = [
      'audio/mp3', 'audio/mpeg', 'audio/wav', 'audio/wave', 
      'audio/x-wav', 'audio/m4a', 'audio/x-m4a', 'audio/flac',
      'video/mp4', 'video/avi', 'video/quicktime', 'video/x-msvideo',
      'video/x-matroska'
    ];
    const validExtensions = ['.mp3', '.wav', '.m4a', '.flac', '.mp4', '.avi', '.mov', '.mkv'];
    
    return validTypes.includes(file.type) || 
           validExtensions.some(ext => file.name.toLowerCase().endsWith(ext));
  }

  private formatFileSize(bytes: number): string {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  }

  private async startTranscription() {
    if (!this.selectedFile) {
      this.showError('ファイルが選択されていません', 
        'まず音声ファイルを選択してください');
      return;
    }

    try {
      this.showProgress();
      this.updateProgress(10, 'ファイルを準備中...');

      // Read file data as array buffer
      const fileData = await this.selectedFile.arrayBuffer();
      const uint8Array = new Uint8Array(fileData);
      const fileDataArray = Array.from(uint8Array);

      // Save file temporarily on the backend
      const tempFilePath = await invoke<string>('save_temp_file', {
        fileData: fileDataArray,
        fileName: this.selectedFile.name
      });

      this.updateProgress(30, 'Whisperエンジンを初期化中...');
      this.updateProgress(50, '音声ファイルを処理中...');
      
      // Start transcription with temp file path (direct script execution)
      const result = await invoke<string>('transcribe_audio', { 
        filePath: tempFilePath
      });

      this.updateProgress(100, '転写完了');
      this.showResult(result);
      
    } catch (error) {
      console.error('Transcription error:', error);
      this.showError('転写に失敗しました', 
        `エラー詳細: ${error}`);
    }
  }

  private async copyResult() {
    try {
      await navigator.clipboard.writeText(this.resultContent.textContent || '');
      this.updateStatus('コピー完了', 'success', 'クリップボードにコピーされました');
      
      // Show feedback
      const originalText = this.copyBtn.innerHTML;
      this.copyBtn.innerHTML = '<span>✅</span> コピー済み';
      setTimeout(() => {
        this.copyBtn.innerHTML = originalText;
      }, 2000);
    } catch (error) {
      this.showError('コピーに失敗しました', 'クリップボードへのアクセスができません');
    }
  }

  private async saveResult() {
    if (!this.selectedFile) {
      this.showError('ファイル情報が見つかりません', 'もう一度転写を実行してください');
      return;
    }

    try {
      const content = this.resultContent.textContent || '';
      // First try to save with dialog
      try {
        const savedPath = await invoke<string>('save_transcription', {
          content: content,
          originalFileName: this.selectedFile.name
        });
        
        this.updateStatus('保存完了', 'success', savedPath);
        
        // Show feedback
        const originalText = this.saveBtn.innerHTML;
        this.saveBtn.innerHTML = '<span>✅</span> 保存済み';
        setTimeout(() => {
          this.saveBtn.innerHTML = originalText;
        }, 2000);
        return;
      } catch (firstError) {
        console.log('First save attempt failed:', firstError);
        
        // Fallback: Save directly to Downloads
        try {
          const downloadsPath = await invoke<string>('save_to_downloads_direct', {
            content: content,
            fileName: `${this.selectedFile.name.split('.')[0]}.txt`
          });
          
          this.updateStatus('保存完了', 'success', downloadsPath);
          
          // Show feedback
          const originalText = this.saveBtn.innerHTML;
          this.saveBtn.innerHTML = '<span>✅</span> 保存済み';
          setTimeout(() => {
            this.saveBtn.innerHTML = originalText;
          }, 2000);
          return;
        } catch (secondError) {
          console.error('Downloads save also failed:', secondError);
          throw secondError;
        }
      }
    } catch (error) {
      console.error('Save error:', error);
      this.showError('保存に失敗しました', `エラー詳細: ${error}`);
    }
  }

  private resetApp() {
    this.selectedFile = null;
    this.hideResults();
    this.hideError();
    this.hideProgress();
    
    // Reset drop zone
    this.dropZone.querySelector('.drop-icon')!.textContent = '📁';
    this.dropZone.querySelector('.drop-text')!.textContent = 'ファイルをここにドロップ';
    this.dropZone.querySelector('.drop-hint')!.textContent = 'または クリックして選択';

    // Reset button
    this.actionBtn.disabled = true;
    this.btnText.textContent = 'ファイルを選択してください';
    this.btnIcon.textContent = '🚀';

    // Reset file input
    this.fileInput.value = '';

    this.updateStatus('準備完了', 'success', '音声ファイルを選択してください');
  }

  private retryTranscription() {
    this.hideError();
    this.startTranscription();
  }

  // UI State Management Methods
  private showProgress() {
    this.progressContainer.classList.remove('hidden');
    this.actionBtn.disabled = true;
    this.dropZone.classList.add('disabled');
  }

  private hideProgress() {
    this.progressContainer.classList.add('hidden');
    this.actionBtn.disabled = false;
    this.dropZone.classList.remove('disabled');
  }

  private updateProgress(percentage: number, message: string) {
    this.progressFill.style.width = `${percentage}%`;
    this.progressText.textContent = message;
  }

  private showResult(result: string) {
    this.hideProgress();
    this.hideError();
    this.resultContent.textContent = result;
    this.resultCard.classList.add('show');
    this.updateStatus('転写完了', 'success', '結果をコピーまたは新しい転写を開始');
  }

  private hideResults() {
    this.resultCard.classList.remove('show');
  }

  private showError(title: string, message: string) {
    this.hideProgress();
    this.hideResults();
    this.errorTitle.textContent = title;
    this.errorMessage.textContent = message;
    this.errorCard.classList.add('show');
    this.updateStatus('エラー', 'error', title);
    
    // Re-enable controls
    this.actionBtn.disabled = !this.selectedFile;
    this.dropZone.classList.remove('disabled');
  }

  private hideError() {
    this.errorCard.classList.remove('show');
  }

  private async loadGpuInfo() {
    try {
      const gpuInfo = await invoke<string>('get_gpu_info');
      this.gpuStatus.textContent = gpuInfo;
    } catch (error) {
      console.error('Failed to load GPU info:', error);
      this.gpuStatus.textContent = '💻 GPU情報の取得に失敗しました';
    }
  }

  private updateStatus(title: string, type: 'success' | 'processing' | 'error', message?: string) {
    this.statusTitle.textContent = title;
    if (message) {
      this.statusMessage.textContent = message;
    }
    
    // Update status card appearance
    this.statusCard.className = 'status-card';
    if (type === 'processing') {
      this.statusCard.classList.add('warning');
      this.statusIcon.textContent = '⏳';
    } else if (type === 'error') {
      this.statusCard.classList.add('error');
      this.statusIcon.textContent = '❌';
    } else {
      this.statusIcon.textContent = '✅';
    }
  }
}

// アプリケーションの初期化
document.addEventListener('DOMContentLoaded', () => {
  new WebWhisperApp();
});

export default WebWhisperApp;