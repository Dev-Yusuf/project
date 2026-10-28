/* A read-only dictionary playground. All archive content is rendered as text. */
(() => {
    'use strict';
    const terminal = document.querySelector('[data-word-lab]');
    if (!terminal) return;
    const output = terminal.querySelector('[data-lab-output]');
    const form = terminal.querySelector('[data-lab-form]');
    const input = form.elements.word;
    const submit = terminal.querySelector('[data-lab-submit]');
    const history = [];
    let historyIndex = 0;
    let draft = '';
    let activeRequest = null;
    let generation = 0;

    const element = (tag, className, text) => {
        const node = document.createElement(tag);
        if (className) node.className = className;
        if (text !== undefined) node.textContent = text;
        return node;
    };
    const scrollOutput = () => { output.scrollTop = output.scrollHeight; };
    const setBusy = (busy) => {
        input.disabled = busy;
        submit.disabled = busy;
        terminal.setAttribute('aria-busy', String(busy));
    };
    const clear = () => {
        generation += 1;
        activeRequest?.abort();
        activeRequest = null;
        output.replaceChildren(element('p', 'terminal-message', 'Fresh start. Type a word to explore.'));
        setBusy(false);
        input.value = '';
        input.focus({preventScroll: true});
    };
    const entry = (command) => {
        const group = element('div', 'terminal-entry');
        const prompt = element('div', 'terminal-command');
        prompt.append(element('span', 'terminal-command-marker', '›'), element('span', '', command));
        group.append(prompt);
        output.append(group);
        // Keep a long play session from growing the DOM indefinitely.
        while (output.children.length > 12) output.firstElementChild.remove();
        scrollOutput();
        return group;
    };
    const lookup = async (raw) => {
        const word = raw.trim();
        if (!word || activeRequest) return;
        history.push(word);
        if (history.length > 30) history.shift();
        historyIndex = history.length;
        draft = '';
        input.value = '';
        if (word.toLowerCase() === 'clear') { clear(); return; }
        const group = entry(word);
        if (word.toLowerCase() === 'help') {
            group.append(element('p', 'terminal-message', 'Enter an Igala word to see every recorded meaning.'));
            const commands = element('dl', 'terminal-help');
            [['help', 'Show these commands'], ['clear', 'Clear the screen'], ['↑ / ↓', 'Recall a previous word']].forEach(([key, value]) => {
                commands.append(element('dt', '', key), element('dd', '', value));
            });
            group.append(commands);
            scrollOutput();
            input.focus({preventScroll: true});
            return;
        }
        const controller = new AbortController();
        const currentGeneration = generation;
        activeRequest = controller;
        setBusy(true);
        const loading = element('p', 'terminal-message terminal-loading', 'Looking in the archive…');
        group.append(loading);
        scrollOutput();
        const timeout = setTimeout(() => controller.abort(), 8000);
        const search = async (exact) => {
            const url = new URL(terminal.dataset.searchUrl, window.location.origin);
            url.searchParams.set('q', word);
            if (exact) url.searchParams.set('exact', '1');
            const response = await fetch(url, {signal: controller.signal, headers: {'Accept': 'application/json'}});
            if (!response.ok) throw new Error('Lookup unavailable');
            const data = await response.json();
            if (!Array.isArray(data.words)) throw new Error('Unexpected response');
            return data.words;
        };
        try {
            const results = await search(true);
            if (generation !== currentGeneration) return;
            loading.remove();
            if (results.length) {
                results.forEach((result) => {
                    const block = element('div', 'terminal-result');
                    block.append(element('strong', 'terminal-result-word', result.word));
                    if (Array.isArray(result.meanings) && result.meanings.length) {
                        const list = element('ol', 'terminal-definitions');
                        result.meanings.forEach((meaning) => {
                            const definition = element('li');
                            definition.append(element('span', 'terminal-pos', meaning.part_of_speech), document.createTextNode(' ' + meaning.meaning));
                            list.append(definition);
                        });
                        block.append(list);
                    } else {
                        block.append(element('p', 'terminal-message', 'This word has no recorded meaning yet.'));
                    }
                    group.append(block);
                });
            } else {
                group.append(element('p', 'terminal-message', 'No exact match yet. Check the spelling and tone marks.'));
                const suggestions = (await search(false)).slice(0, 5);
                if (generation !== currentGeneration) return;
                if (suggestions.length) {
                    const choices = element('div', 'terminal-suggestions');
                    choices.append(element('span', '', 'Try:'));
                    suggestions.forEach((suggestion) => {
                        const button = element('button', '', suggestion.word);
                        button.type = 'button';
                        button.addEventListener('click', () => { lookup(suggestion.word); });
                        choices.append(button);
                    });
                    group.append(choices);
                }
            }
        } catch (error) {
            if (generation !== currentGeneration) return;
            loading.remove();
            group.append(element('p', 'terminal-message terminal-error', error.name === 'AbortError'
                ? 'That took too long. Please try again.'
                : 'The archive is unavailable right now. Please try again.'));
        } finally {
            clearTimeout(timeout);
            if (generation === currentGeneration) {
                activeRequest = null;
                setBusy(false);
                scrollOutput();
                input.focus({preventScroll: true});
            }
        }
    };
    form.addEventListener('submit', (event) => { event.preventDefault(); lookup(input.value); });
    terminal.querySelector('[data-lab-clear]').addEventListener('click', clear);
    document.querySelectorAll('[data-lab-word]').forEach((button) => {
        button.addEventListener('click', () => { lookup(button.dataset.labWord); });
    });
    input.addEventListener('keydown', (event) => {
        if (event.isComposing) return;
        if (!history.length || !['ArrowUp', 'ArrowDown'].includes(event.key)) return;
        event.preventDefault();
        if (historyIndex === history.length) draft = input.value;
        historyIndex = Math.max(0, Math.min(history.length, historyIndex + (event.key === 'ArrowUp' ? -1 : 1)));
        input.value = historyIndex === history.length ? draft : history[historyIndex];
    });
})();
