// Hero video: autoplay muted unless the visitor prefers reduced motion;
// play/pause and sound buttons. Adapted from brag docs/main.js (MIT, see styles.css).
(() => {
  const vid = document.getElementById('hero-vid');
  const playBtn = document.getElementById('hero-playback');
  const muteBtn = document.getElementById('hero-mute');
  if (!vid || !playBtn || !muteBtn) return;
  const muteLabel = muteBtn.querySelector('.hero-mute-label');
  const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');

  const syncPlay = () => {
    const paused = vid.paused;
    playBtn.dataset.mode = paused ? 'play' : 'pause';
    playBtn.setAttribute('aria-label', paused ? 'Запустить ролик' : 'Остановить ролик');
    playBtn.title = playBtn.getAttribute('aria-label');
  };
  const syncMute = () => {
    muteBtn.setAttribute('aria-pressed', vid.muted ? 'true' : 'false');
    muteBtn.setAttribute('aria-label', vid.muted ? 'Включить звук' : 'Выключить звук');
    if (muteLabel) muteLabel.textContent = vid.muted ? 'нажмите для звука' : 'звук включён';
  };
  const tryPlay = () => {
    const p = vid.play();
    if (p && p.catch) p.catch(syncPlay);
  };
  const applyMotionPreference = () => {
    if (reducedMotion.matches) {
      vid.pause();
      syncPlay();
      return;
    }
    vid.muted = true;
    syncMute();
    tryPlay();
  };

  playBtn.addEventListener('click', () => (vid.paused ? tryPlay() : vid.pause()));
  muteBtn.addEventListener('click', () => {
    vid.muted = !vid.muted;
    if (!vid.muted && vid.paused) tryPlay();
    syncMute();
  });
  vid.addEventListener('play', syncPlay);
  vid.addEventListener('pause', syncPlay);
  applyMotionPreference();
  reducedMotion.addEventListener('change', applyMotionPreference);
})();
