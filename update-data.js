// Nepal Flood Monitor - Data Updater Script
// Run this script on a schedule to refresh data.json with latest figures.
// It fetches from public APIs (ReliefWeb, GDACS) and Wikipedia REST,
// parses relevant numbers, and writes back to data.json preserving history.

const fs = require('fs');
const path = require('path');

// Configuration
const DATA_FILE = path.join(__dirname, 'data.json');
const HISTORY_LIMIT = 30; // keep last 30 death toll entries

// Helper: read current data
function readCurrentData() {
    try {
        const raw = fs.readFileSync(DATA_FILE, 'utf8');
        return JSON.parse(raw);
    } catch (err) {
        console.error('Could not read existing data.json, starting fresh', err);
        return null;
    }
}

// Helper: fetch JSON from URL with timeout
async function fetchJson(url, timeoutMs = 10000) {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), timeoutMs);
    try {
        const response = await fetch(url, { signal: controller.signal });
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        return await response.json();
    } finally {
        clearTimeout(timeout);
    }
}

// 1. ReliefWeb API - get latest situation report
async function fetchReliefWebData() {
    // ReliefWeb API for Nepal flood 2026 (hypothetical ID, adjust as needed)
    const url = 'https://api.reliefweb.int/v1/reports?appname=rwint-user-0&filter[field]=country&filter[value]=Nepal&filter[field]=disaster_type&filter[value]=flood&limit=3';
    try {
        const data = await fetchJson(url);
        // Extract key figures from report titles or summaries (simplified)
        // In a real script, you would parse the description text for numbers.
        // We'll simulate extraction: find "deaths" or "casualties" in summary.
        let deaths = null, missing = null, rescued = null;
        if (data.data && data.data.length > 0) {
            const latest = data.data[0];
            const summary = latest.fields.body || latest.fields.title || '';
            // Very naive regex extraction; real implementation would be more robust.
            const deathMatch = summary.match(/(\d+)\s+deaths?/i);
            if (deathMatch) deaths = parseInt(deathMatch[1]);
            const missingMatch = summary.match(/(\d+)\s+missing/i);
            if (missingMatch) missing = parseInt(missingMatch[1]);
            const rescuedMatch = summary.match(/(\d+)\s+rescued/i);
            if (rescuedMatch) rescued = parseInt(rescuedMatch[1]);
            return { deaths, missing, rescued, source: 'ReliefWeb' };
        }
        return null;
    } catch (err) {
        console.error('ReliefWeb fetch failed:', err.message);
        return null;
    }
}

// 2. GDACS API - event data (hypothetical flood event ID 100123)
async function fetchGDACSData() {
    const url = 'https://www.gdacs.org/gdacsapi/api/events/eventdata/100123';
    try {
        const data = await fetchJson(url);
        // GDACS returns event severity, affected population etc.
        // Extract relevant fields: maybe affected_population
        const affected = data.properties?.affected_population || null;
        return { affected_population: affected, source: 'GDACS' };
    } catch (err) {
        console.error('GDACS fetch failed:', err.message);
        return null;
    }
}

// 3. Wikipedia REST API - for live event page summary (if available)
async function fetchWikipediaData() {
    const title = '2026_Nepal_floods'; // hypothetical page
    const url = `https://en.wikipedia.org/api/rest_v1/page/summary/${title}`;
    try {
        const data = await fetchJson(url);
        const extract = data.extract || '';
        // Extract numbers from summary (simple regex)
        const deathMatch = extract.match(/(\d+)\s+deaths?/i);
        const missingMatch = extract.match(/(\d+)\s+missing/i);
        const rescuedMatch = extract.match(/(\d+)\s+rescued/i);
        return {
            deaths: deathMatch ? parseInt(deathMatch[1]) : null,
            missing: missingMatch ? parseInt(missingMatch[1]) : null,
            rescued: rescuedMatch ? parseInt(rescuedMatch[1]) : null,
            source: 'Wikipedia'
        };
    } catch (err) {
        console.error('Wikipedia fetch failed:', err.message);
        return null;
    }
}

// Main update function
async function updateData() {
    console.log('Starting data update...');
    const current = readCurrentData();
    const newData = current || {
        last_updated: new Date().toISOString(),
        situation_summary: "Flash floods along the Bhotekoshi River in Rasuwa and Sindhupalchok districts.",
        stats: {},
        death_toll_history: [],
        timeline: [],
        district_breakdown: [],
        relief_tracker: { groups: {} },
        sources: []
    };

    // Fetch external data (parallel)
    const [relief, gdacs, wiki] = await Promise.all([
        fetchReliefWebData(),
        fetchGDACSData(),
        fetchWikipediaData()
    ]);

    // Merge findings: prioritize ReliefWeb for death toll, use others for corroboration.
    let updatedDeaths = null;
    if (relief && relief.deaths) updatedDeaths = relief.deaths;
    else if (wiki && wiki.deaths) updatedDeaths = wiki.deaths;
    else if (newData.stats.deaths) updatedDeaths = newData.stats.deaths.value;

    // Update stats if new value found and different
    if (updatedDeaths !== null) {
        if (!newData.stats.deaths) newData.stats.deaths = {};
        if (newData.stats.deaths.value !== updatedDeaths) {
            newData.stats.deaths.value = updatedDeaths;
            newData.stats.deaths.source = relief?.source || wiki?.source || 'Unknown';
            newData.stats.deaths.source_url = 'https://reliefweb.int'; // placeholder
            // Append to history
            const historyEntry = {
                timestamp: new Date().toISOString(),
                deaths: updatedDeaths
            };
            newData.death_toll_history = newData.death_toll_history || [];
            newData.death_toll_history.push(historyEntry);
            // Limit history length
            if (newData.death_toll_history.length > HISTORY_LIMIT) {
                newData.death_toll_history = newData.death_toll_history.slice(-HISTORY_LIMIT);
            }
        }
    }

    // Update last_updated timestamp
    newData.last_updated = new Date().toISOString();

    // Write back to data.json
    fs.writeFileSync(DATA_FILE, JSON.stringify(newData, null, 2), 'utf8');
    console.log('Data updated successfully at', newData.last_updated);
}

// Run update
updateData().catch(err => {
    console.error('Update failed:', err);
    process.exit(1);
});