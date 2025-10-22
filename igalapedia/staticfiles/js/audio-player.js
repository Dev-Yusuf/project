// Audio Player Module
const AudioPlayer = {
    currentAudio: null,

    init: function() {
        this.bindVolumeIcons();
    },

    bindVolumeIcons: function() {
        const volumeIcons = document.querySelectorAll('.volume-icon');
        
        volumeIcons.forEach(icon => {
            icon.addEventListener('click', (e) => {
                const audioUrl = icon.dataset.audio;
                
                if (!audioUrl) {
                    this.showNoAudioMessage();
                    return;
                }
                
                this.playAudio(audioUrl, icon);
            });
            
            // Add hover effect to show it's clickable
            icon.style.cursor = 'pointer';
        });
    },

    playAudio: function(audioUrl, icon) {
        // Stop current audio if playing
        if (this.currentAudio) {
            this.currentAudio.pause();
            this.currentAudio.currentTime = 0;
        }

        // Create and play new audio
        this.currentAudio = new Audio(audioUrl);
        
        // Visual feedback: change icon while playing
        const originalClass = icon.className;
        icon.className = 'fas fa-pause-circle volume-icon playing';
        
        this.currentAudio.play()
            .then(() => {
                console.log('Audio playing...');
            })
            .catch(error => {
                console.error('Error playing audio:', error);
                this.showErrorMessage();
                icon.className = originalClass;
            });

        // Reset icon when audio ends
        this.currentAudio.addEventListener('ended', () => {
            icon.className = originalClass;
        });
    },

    showNoAudioMessage: function() {
        const message = document.createElement('div');
        message.className = 'audio-notification';
        message.textContent = '🎵 Audio pronunciation not available for this word yet.';
        message.style.cssText = `
            position: fixed;
            top: 100px;
            right: 20px;
            background: #fff3cd;
            color: #856404;
            padding: 15px 20px;
            border-radius: 8px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
            z-index: 9999;
            font-size: 14px;
            font-weight: 500;
            animation: slideIn 0.3s ease-out;
        `;
        
        document.body.appendChild(message);
        
        setTimeout(() => {
            message.style.animation = 'slideOut 0.3s ease-out';
            setTimeout(() => message.remove(), 300);
        }, 3000);
    },

    showErrorMessage: function() {
        const message = document.createElement('div');
        message.className = 'audio-notification error';
        message.textContent = '❌ Error playing audio. Please try again.';
        message.style.cssText = `
            position: fixed;
            top: 100px;
            right: 20px;
            background: #f8d7da;
            color: #721c24;
            padding: 15px 20px;
            border-radius: 8px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
            z-index: 9999;
            font-size: 14px;
            font-weight: 500;
        `;
        
        document.body.appendChild(message);
        
        setTimeout(() => message.remove(), 3000);
    }
};

// Add CSS animations
const style = document.createElement('style');
style.textContent = `
    @keyframes slideIn {
        from {
            transform: translateX(400px);
            opacity: 0;
        }
        to {
            transform: translateX(0);
            opacity: 1;
        }
    }
    
    @keyframes slideOut {
        from {
            transform: translateX(0);
            opacity: 1;
        }
        to {
            transform: translateX(400px);
            opacity: 0;
        }
    }

    .volume-icon {
        transition: all 0.3s ease;
    }

    .volume-icon:hover {
        color: var(--accent-color) !important;
        transform: scale(1.1);
    }

    .volume-icon.playing {
        color: var(--accent-color) !important;
        animation: pulse 1s infinite;
    }

    @keyframes pulse {
        0%, 100% {
            opacity: 1;
        }
        50% {
            opacity: 0.6;
        }
    }
`;
document.head.appendChild(style);

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    AudioPlayer.init();
});

