/* One audio element and queue survive all navigation within /music/. */
(() => {
    'use strict';
    const root = document.querySelector('[data-music-root]');
    if (!root) return;
    const content = document.getElementById('music-content');
    const audio = document.getElementById('music-audio');
    const player = document.querySelector('[data-player]');
    const panel = document.getElementById('music-queue');
    const toast = document.querySelector('.music-toast');
    const csrf = document.querySelector('#music-csrf input').value;
    const $ = selector => document.querySelector(selector);
    const time = seconds => `${Math.floor((seconds || 0) / 60)}:${String(Math.floor((seconds || 0) % 60)).padStart(2, '0')}`;
    let pageTracks = [], queue = [], index = -1, shuffle = false, repeat = 0;
    let playVersion = 0, navigationVersion = 0, navigationRequest, playbackRequest, searchTimer, toastTimer;
    let savedPosition = 0, renewed = false, isLoading = false;
    audio.volume = 0.8;

    const notify = message => {
        clearTimeout(toastTimer); toast.textContent = message; toast.hidden = false;
        toastTimer = setTimeout(() => { toast.hidden = true; }, 5000);
    };
    const remember = () => {
        try { sessionStorage.setItem('igala-music-queue', JSON.stringify({queue, index, shuffle, repeat, position: audio.currentTime || savedPosition})); } catch (_) {}
    };
    const renderQueue = () => {
        const list = $('[data-queue-list]'); list.replaceChildren();
        queue.forEach((song, number) => {
            const row = document.createElement('li');
            if (number === index) row.className = 'is-current';
            const play = document.createElement('button'); play.type = 'button';
            play.textContent = `${song.title} · ${song.artist}`;
            play.addEventListener('click', () => start(number));
            const remove = document.createElement('button'); remove.type = 'button'; remove.textContent = '×';
            remove.setAttribute('aria-label', `Remove ${song.title} from queue`);
            remove.addEventListener('click', () => {
                if (number === index) { audio.pause(); audio.removeAttribute('src'); audio.load(); playVersion++; playbackRequest?.abort(); isLoading = false; savedPosition = 0; index = -1; }
                else if (number < index) index--;
                queue.splice(number, 1); render(); remember();
            });
            row.append(play, remove); list.append(row);
        });
        $('[data-queue-empty]').hidden = queue.length > 0;
    };
    const render = () => {
        player.setAttribute('aria-busy',String(isLoading));
        const song = queue[index];
        const title = $('[data-player-title]'), artist = $('[data-player-artist]'), art = $('[data-player-art]');
        title.textContent = song?.title || 'Choose a track'; artist.textContent = song?.artist || 'Igala Music';
        if (song) { title.href = song.url; artist.href = song.artist_url; title.dataset.musicLink = ''; artist.dataset.musicLink = ''; }
        else { title.removeAttribute('href'); artist.removeAttribute('href'); }
        art.replaceChildren();
        if (song?.cover) { const image = document.createElement('img'); image.src = song.cover; image.alt = ''; art.append(image); }
        else { const symbol = document.createElement('span'); symbol.textContent = '♫'; art.append(symbol); }
        document.querySelectorAll('[data-toggle-play],[data-previous],[data-next],[data-shuffle],[data-repeat],[data-seek]').forEach(button => { button.disabled = !song; });
        const playing = !audio.paused;
        $('[data-toggle-play]').setAttribute('aria-label', playing ? 'Pause' : 'Play');
        $('[data-toggle-play]').innerHTML = `<i class="bx ${playing ? 'bx-pause' : 'bx-play'}" aria-hidden="true"></i>`;
        $('[data-shuffle]').setAttribute('aria-pressed', String(shuffle));
        $('[data-repeat]').setAttribute('aria-pressed', String(repeat !== 0));
        $('[data-repeat]').setAttribute('aria-label', ['Repeat off', 'Repeat all', 'Repeat one'][repeat]);
        $('[data-repeat]').textContent = repeat === 2 ? '↻¹' : '↻';
        $('[data-total-time]').textContent = time(Number.isFinite(audio.duration) ? audio.duration : song?.duration);
        if (!song) { $('[data-current-time]').textContent = '0:00'; $('[data-seek]').value = 0; $('[data-seek]').max = 100; }
        document.querySelectorAll('[data-track-row]').forEach(row => row.classList.toggle('is-playing', Boolean(song && Number(row.dataset.trackRow) === song.id && playing)));
        renderQueue();
        if ('mediaSession' in navigator && song && 'MediaMetadata' in window) {
            navigator.mediaSession.metadata = new MediaMetadata({title:song.title, artist:song.artist, artwork:song.cover ? [{src:song.cover}] : []});
        }
        if ('mediaSession' in navigator && !song) navigator.mediaSession.metadata = null;
    };
    const start = async (number, position = 0, retry = false) => {
        if (!queue[number]) return;
        playbackRequest?.abort();
        playbackRequest = new AbortController();
        const request = playbackRequest;
        const timeout = setTimeout(() => request.abort(), 10000);
        const token = ++playVersion;
        audio.pause(); audio.removeAttribute('src'); audio.load();
        index = number; savedPosition = position; isLoading = true; renewed = retry; render(); remember();
        try {
            const response = await fetch(queue[index].playback, {headers:{Accept:'application/json'}, cache:'no-store', signal:request.signal});
            if (!response.ok) throw new Error(response.status === 404 ? 'This track is no longer available.' : 'Playback is unavailable. Please try again.');
            const song = await response.json();
            if (token !== playVersion) return;
            queue[index] = {id:song.id, title:song.title, artist:song.artist, artist_url:song.artist_url, url:song.url, cover:song.cover, duration:song.duration, playback:song.playback};
            audio.src = song.stream;
            if (position > 0) audio.addEventListener('loadedmetadata', () => {
                if (token === playVersion) audio.currentTime = Math.min(position, Math.max(0, audio.duration - 0.1));
            }, {once:true});
            await audio.play();
            if (token !== playVersion) { return; }
            isLoading = false; savedPosition = 0; render(); remember();
        } catch (error) {
            if (token !== playVersion) return;
            isLoading = false; render(); notify(error.name === 'AbortError' ? 'Playback took too long. Please try again.' : error.message || 'Unable to play this track.');
        } finally { clearTimeout(timeout); }
    };
    const toggle = () => {
        if (!queue[index]) return;
        if (!audio.paused) { audio.pause(); remember(); return; }
        if (!audio.getAttribute('src')) start(index, savedPosition);
        else audio.play().catch(() => notify('Tap Play to resume listening.'));
    };
    const next = (automatic = false) => {
        if (!queue.length || index < 0) return;
        if (automatic && repeat === 2) { audio.currentTime = 0; audio.play().catch(() => notify('Tap Play to resume.')); return; }
        let target = index + 1;
        if (shuffle && queue.length > 1) { target = (index + 1 + Math.floor(Math.random() * (queue.length - 1))) % queue.length; }
        else if (target >= queue.length) {
            if (repeat === 1) target = 0;
            else { audio.pause(); render(); return; }
        }
        start(target);
    };
    const closeExpanded = () => {
        player.classList.remove('is-expanded'); player.removeAttribute('role'); player.removeAttribute('aria-modal');
        root.inert = false; $('.site-nav').inert = false;
        document.body.style.overflow = '';
        $('[data-player-expand]').setAttribute('aria-expanded','false'); $('[data-player-expand]').setAttribute('aria-label','Expand player');
        $('[data-player-expand]').textContent = '⌃';
    };
    const queueVisibility = visible => {
        panel.hidden = !visible; $('[data-queue-toggle]').setAttribute('aria-expanded', String(visible));
        if (visible) { closeExpanded(); $('[data-queue-close]').focus(); }
    };
    const loadPage = async (url, options = {}) => {
        clearTimeout(searchTimer); navigationRequest?.abort();
        navigationRequest = new AbortController(); const token = ++navigationVersion;
        const fetchUrl = new URL(url, location.origin);
        const method = options.method || 'GET';
        if (method === 'GET') fetchUrl.searchParams.set('fragment','1');
        const focusSearch = options.live && document.activeElement?.id === 'music-query';
        const caret = focusSearch ? document.activeElement.selectionStart : null;
        content.setAttribute('aria-busy','true');
        try {
            const response = await fetch(fetchUrl, {method, body:options.body, signal:navigationRequest.signal,
                headers: method === 'POST' ? {'X-CSRFToken':csrf} : {}});
            if (token !== navigationVersion) return;
            if (new URL(response.url).origin !== location.origin || !new URL(response.url).pathname.startsWith('/music/')) { location.assign(response.url); return; }
            const html = await response.text();
            if (token !== navigationVersion) return;
            const parsed = new DOMParser().parseFromString(html,'text/html');
            const view = parsed.querySelector('.music-view');
            if (!view || !response.ok) throw new Error('Could not open this music page. Please try again.');
            content.replaceChildren(document.importNode(view,true));
            const destination = new URL(response.url); destination.searchParams.delete('fragment');
            if (!options.history) history[options.live ? 'replaceState' : 'pushState'](null,'',destination);
            updatePage();
            if (focusSearch) {
                const field = $('#music-query'); field.focus({preventScroll:true});
                if (caret !== null) field.setSelectionRange(caret,caret);
            } else { content.focus({preventScroll:true}); window.scrollTo({top:0,behavior:'instant'}); }
        } catch (error) { if (token === navigationVersion && error.name !== 'AbortError') notify(error.message || 'Connection interrupted. Please try again.'); }
        finally { if (token === navigationVersion) content.removeAttribute('aria-busy'); }
    };
    const updatePage = () => {
        try { pageTracks = JSON.parse($('#music-page-tracks')?.textContent || '[]'); } catch (_) { pageTracks = []; }
        const section = $('.music-view')?.dataset.section;
        document.querySelectorAll('.music-nav a').forEach(link => {
            const match = link.dataset.section === section || (section === 'artist' && link.dataset.section === 'artists') ||
                (section === 'release' && link.dataset.section === 'releases') || (section === 'playlist' && link.dataset.section === 'library');
            if (match) link.setAttribute('aria-current','page'); else link.removeAttribute('aria-current');
        });
        const heading = content.querySelector('h1')?.innerText || 'Music';
        document.title = `${heading.replace(/\s+/g,' ').replace(/\.$/,'')} · Igala Music`;
        render();
    };
    const post = async (url, body) => {
        const response = await fetch(url, {method:'POST', body, headers:{'X-CSRFToken':csrf}});
        if (response.redirected && !new URL(response.url).pathname.startsWith('/music/')) { location.assign(response.url); throw new Error('Please sign in.'); }
        if (!response.ok) throw new Error('Could not save your change. Please try again.');
        return response;
    };
    document.addEventListener('click', async event => {
        const button = event.target.closest('button,a'); if (!button) return;
        const musicLink = button.matches('a[data-music-link]') && button.href;
        if (musicLink && !event.ctrlKey && !event.metaKey && !event.shiftKey && !event.altKey && event.button === 0) {
            const url = new URL(button.href);
            if (url.origin === location.origin && url.pathname.startsWith('/music/')) { event.preventDefault(); closeExpanded(); loadPage(url); return; }
        }
        if (button.hasAttribute('data-play') || button.hasAttribute('data-play-all')) {
            const number = button.hasAttribute('data-play-all') ? 0 : pageTracks.findIndex(song => song.id === Number(button.dataset.play));
            if (number >= 0 && pageTracks.length) { queue = [...pageTracks]; start(number); }
        }
        if (button.hasAttribute('data-enqueue')) {
            const song = pageTracks.find(song => song.id === Number(button.dataset.enqueue));
            if (song) { queue.push(song); renderQueue(); remember(); notify('Added to queue.'); }
        }
        if (button.hasAttribute('data-save')) {
            const body = new FormData(); body.set('saved',button.getAttribute('aria-pressed') === 'true' ? '0':'1');
            button.disabled = true;
            try { const data = await (await post(button.dataset.url,body)).json(); button.setAttribute('aria-pressed',String(data.saved)); button.innerHTML = `<i class="bx ${data.saved ? 'bxs-heart':'bx-heart'}" aria-hidden="true"></i>`; notify(data.saved ? 'Added to liked tracks.':'Removed from liked tracks.'); }
            catch (error) { notify(error.message); } finally { button.disabled = false; }
        }
    });
    document.addEventListener('submit', async event => {
        const form = event.target;
        if (form.matches('[data-music-search]')) { event.preventDefault(); const url = new URL(form.action); url.search = new URLSearchParams(new FormData(form)).toString(); loadPage(url); return; }
        if (!form.matches('[data-music-form],[data-add-to-playlist]')) return;
        event.preventDefault();
        if (form.dataset.confirm && !window.confirm(form.dataset.confirm)) return;
        const body = new FormData(form);
        if (event.submitter?.name) body.set(event.submitter.name,event.submitter.value);
        let url = form.action;
        if (form.hasAttribute('data-add-to-playlist')) {
            url = form.elements.playlist.value;
            if (!url) { notify('Create a playlist in Your library first.'); return; }
            try { await post(url,body); notify('Added to playlist.'); } catch (error) { notify(error.message); }
            return;
        }
        const submit = event.submitter; if (submit) submit.disabled = true;
        const progress = form.querySelector('.music-upload-status'); if (progress) progress.hidden = false;
        await loadPage(url,{method:'POST',body});
        if (submit?.isConnected) submit.disabled = false;
        if (progress?.isConnected) progress.hidden = true;
    });
    document.addEventListener('input', event => {
        if (event.target.id !== 'music-query') return;
        clearTimeout(searchTimer); navigationRequest?.abort(); navigationVersion++;
        searchTimer = setTimeout(() => { const form = event.target.form; const url = new URL(form.action); url.search = new URLSearchParams(new FormData(form)).toString(); loadPage(url,{live:true}); },250);
    });
    document.addEventListener('change', event => {
        if (event.target.id === 'music-genre') event.target.form.requestSubmit();
    });
    $('[data-toggle-play]').addEventListener('click',toggle);
    $('[data-next]').addEventListener('click',() => next());
    $('[data-previous]').addEventListener('click',() => { if (audio.currentTime > 3) audio.currentTime = 0; else if (index > 0) start(index - 1); });
    $('[data-shuffle]').addEventListener('click',() => { shuffle = !shuffle; render(); remember(); });
    $('[data-repeat]').addEventListener('click',() => { repeat = (repeat + 1) % 3; render(); remember(); });
    $('[data-seek]').addEventListener('input',event => { const position = Number(event.target.value); if (audio.getAttribute('src') && Number.isFinite(audio.duration)) audio.currentTime = position; else savedPosition = position; $('[data-current-time]').textContent = time(position); remember(); });
    $('[data-volume]').addEventListener('input',event => { audio.volume = Number(event.target.value); audio.muted = false; $('[data-mute]').setAttribute('aria-label','Mute'); });
    $('[data-mute]').addEventListener('click',() => { audio.muted = !audio.muted; $('[data-mute]').setAttribute('aria-label',audio.muted ? 'Unmute':'Mute'); $('[data-mute]').innerHTML = `<i class="bx ${audio.muted ? 'bx-volume-mute':'bx-volume-full'}" aria-hidden="true"></i>`; });
    $('[data-queue-toggle]').addEventListener('click',() => queueVisibility(panel.hidden));
    $('[data-queue-close]').addEventListener('click',() => { queueVisibility(false); $('[data-queue-toggle]').focus(); });
    $('[data-queue-clear]').addEventListener('click',() => { playVersion++; playbackRequest?.abort(); isLoading=false; audio.pause(); audio.removeAttribute('src'); audio.load(); queue=[]; index=-1; savedPosition=0; render(); remember(); });
    $('[data-player-expand]').addEventListener('click',() => {
        if (player.classList.contains('is-expanded')) { closeExpanded(); return; }
        queueVisibility(false); player.classList.add('is-expanded'); player.setAttribute('role','dialog'); player.setAttribute('aria-modal','true');
        root.inert = true; $('.site-nav').inert = true;
        document.body.style.overflow = 'hidden';
        $('[data-player-expand]').setAttribute('aria-expanded','true'); $('[data-player-expand]').setAttribute('aria-label','Collapse player');
        $('[data-player-expand]').textContent = '⌄';
    });
    document.addEventListener('keydown',event => {
        if (event.key === 'Escape') { closeExpanded(); queueVisibility(false); }
        if (event.key === 'Tab' && player.classList.contains('is-expanded')) {
            const controls = [...player.querySelectorAll('a[href],button:not(:disabled),input:not(:disabled)')].filter(item => item.getClientRects().length);
            const first = controls[0], last = controls[controls.length-1];
            if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus(); }
            else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
        }
    });
    audio.addEventListener('play',() => { render(); });
    audio.addEventListener('pause',() => { render(); remember(); });
    audio.addEventListener('loadedmetadata',() => { $('[data-seek]').max=String(audio.duration || queue[index]?.duration || 100); render(); });
    audio.addEventListener('timeupdate',() => { $('[data-current-time]').textContent=time(audio.currentTime); $('[data-seek]').value=audio.currentTime; if (Math.floor(audio.currentTime) % 5 === 0) remember(); });
    audio.addEventListener('ended',() => next(true));
    audio.addEventListener('error',() => { if (!audio.getAttribute('src') || isLoading) return; if (!renewed && queue[index]) start(index,audio.currentTime,true); else notify('This audio could not be played. Try another track.'); });
    document.addEventListener('play',event => { if (event.target === audio) document.querySelectorAll('audio,video').forEach(other => { if (other !== audio) other.pause(); }); else if (event.target instanceof HTMLMediaElement) audio.pause(); },true);
    window.addEventListener('popstate',() => loadPage(location.href,{history:true}));
    window.addEventListener('pagehide',() => { remember(); audio.pause(); });
    window.addEventListener('resize',() => { if (innerWidth > 767) closeExpanded(); });
    if ('mediaSession' in navigator) {
        for (const [action,handler] of Object.entries({play:toggle,pause:() => audio.pause(),nexttrack:() => next(),previoustrack:() => { if (index > 0) start(index-1); }})) {
            try { navigator.mediaSession.setActionHandler(action,handler); } catch (_) {}
        }
    }
    try {
        const restored = JSON.parse(sessionStorage.getItem('igala-music-queue') || 'null');
        if (restored && Array.isArray(restored.queue)) {
            queue=restored.queue.filter(song => Number.isInteger(song.id) && song.playback === `/music/api/tracks/${song.id}/play/`).slice(0,300);
            index=Math.min(queue.length-1,Math.max(-1,Number(restored.index)||0)); savedPosition=Math.max(0,Number(restored.position)||0);
            shuffle=Boolean(restored.shuffle); repeat=[0,1,2].includes(restored.repeat) ? restored.repeat:0;
        }
    } catch (_) {}
    updatePage();
    if (savedPosition && queue[index]) { $('[data-current-time]').textContent=time(savedPosition); $('[data-seek]').max=queue[index].duration; $('[data-seek]').value=savedPosition; }
})();
