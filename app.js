/* ============================================================
   NEPAL FLOOD 2026
   APP.JS — MILESTONE 1.5
   UI LOCKED
============================================================ */

"use strict";


/* ============================================================
   DOM REFERENCES
============================================================ */

const els = {
  updated: document.getElementById("updated"),

  rainValue: document.getElementById("rainValue"),
  rainStation: document.getElementById("rainStation"),

  riverValue: document.getElementById("riverValue"),
  riverStation: document.getElementById("riverStation"),
  riverThreshold: document.getElementById("riverThreshold"),
  warningStatus: document.getElementById("warningStatus"),

  deaths: document.getElementById("deaths"),
  missing: document.getElementById("missing"),
  injured: document.getElementById("injured"),

  homes: document.getElementById("homes"),
  bridges: document.getElementById("bridges"),

  riverRows: document.getElementById("riverRows"),
  affectedWeather: document.getElementById("affectedWeather"),

  teams: document.getElementById("teams"),
  rescued: document.getElementById("rescued"),
  vehicles: document.getElementById("vehicles"),
  relief: document.getElementById("relief"),

  operationsStatus: document.getElementById("operationsStatus"),
  operationsBar: document.getElementById("operationsBar"),

  ticker: document.getElementById("ticker"),

  langToggle: document.getElementById("langToggle"),
  themeToggle: document.getElementById("themeToggle"),
  themeIcon: document.getElementById("themeIcon")
};


/* ============================================================
   FALLBACK DATA
============================================================ */

const FALLBACK = {

  updated: "2026-08-28T17:00:00+05:45",

  status: "LIVE",

  rainfall: {
    max_24h_mm: 117,
    station: "Gobre",
    source: "DHM rainfall monitoring"
  },

  river: {
    max_level_m: 7.2,
    basin: "Karnali",
    station: "Chisapani",
    overall_warning: "NORMAL"
  },

  rivers: [

    {
      name: "Karnali",
      basin: "Karnali",
      station: "Chisapani",
      water_level_m: 7.2,
      warning_level_m: 10,
      danger_level_m: 10.8,
      status: "NORMAL",
      trend: "Rising",
      source: "DHM River Watch"
    },

    {
      name: "Narayani",
      basin: "Narayani",
      station: "Devghat",
      water_level_m: 4.7,
      warning_level_m: 7.3,
      danger_level_m: 9,
      status: "NORMAL",
      trend: "Rising",
      source: "DHM River Watch"
    },

    {
      name: "Kankai",
      basin: "Kankai",
      station: "Mainachuli",
      water_level_m: 3.1,
      warning_level_m: 3.8,
      danger_level_m: 4.3,
      status: "NORMAL",
      trend: "Rising",
      source: "DHM River Watch"
    },

    {
      name: "Babai",
      basin: "Babai",
      station: "Chepang",
      water_level_m: 2.7,
      warning_level_m: 5.5,
      danger_level_m: 6.8,
      status: "NORMAL",
      trend: "—",
      source: "DHM River Watch"
    },

    {
      name: "Mahakali",
      basin: "Mahakali",
      station: "Parigaon",
      water_level_m: 5.1,
      warning_level_m: 6.8,
      danger_level_m: 8,
      status: "NORMAL",
      trend: "—",
      source: "DHM River Watch"
    }

  ],

  casualties: {
    deaths: 359,
    missing: null,
    injured: null
  },

  damage: {
    homes: null,
    bridges: null
  },

  rescue: {
    teams: null,
    rescued: null,
    vehicles: null,
    relief: null
  },

  weather: [
    {
      place: "Rasuwa",
      value: null,
      note: "DHM forecast not published for district"
    },
    {
      place: "Nuwakot",
      value: null,
      note: "DHM station monitoring available"
    },
    {
      place: "Dhading",
      value: null,
      note: "DHM station monitoring available"
    },
    {
      place: "Dhunche",
      value: null,
      note: "DHM forecast not published"
    }
  ],

  ticker:
    "Official DHM warnings are in effect. Verify local conditions before travel. Emergency flood information: DHM toll-free 1155."

};


/* ============================================================
   LANGUAGE
============================================================ */

const I18N = {

  en: {

    title:
      "NEPAL FLOOD 2026 | LIVE SITUATION DASHBOARD",

    lastUpdated:
      "LAST UPDATED",

    live:
      "LIVE",

    dataSource:
      "DATA SOURCE: DHM • NDRRMA • Nepal Police",

    maxRain:
      "MAX 24H RAINFALL",

    dhmRain:
      "DHM rainfall monitoring",

    maxRiver:
      "MAX RIVER LEVEL",

    warningStatus:
      "WARNING STATUS",

    dhmWarning:
      "DHM warning system",

    officialWarning:
      "Official warning page",

    casualties:
      "CASUALTIES & IMPACT",

    confirmedDeaths:
      "CONFIRMED<br>DEATHS",

    missingPersons:
      "MISSING<br>PERSONS",

    injuredPersons:
      "INJURED<br>PERSONS",

    damage:
      "DAMAGE TO INFRASTRUCTURE",

    homesDamaged:
      "HOMES<br>DAMAGED",

    bridgesDamaged:
      "BRIDGES<br>DAMAGED",

    damageNote:
      "Only displayed when an official current aggregate is verified.",

    riverLevels:
      "RIVER WATER LEVELS",

    river:
      "RIVER",

    current:
      "CURRENT",

    warning:
      "WARNING",

    danger:
      "DANGER",

    affectedAreas:
      "AFFECTED AREAS — CURRENT DHM MONITORING",

    forecastNote:
      "Official forecast is shown only where DHM publishes a matching location. Monitoring values are not presented as forecasts.",

    rescueRelief:
      "RESCUE & RELIEF OPERATIONS",

    activeTeams:
      "ACTIVE TEAMS",

    peopleRescued:
      "PEOPLE RESCUED",

    rescueVehicles:
      "RESCUE VEHICLES",

    reliefDistributed:
      "RELIEF DISTRIBUTED",

    operationsStatus:
      "Operations status",

    liveUpdates:
      "LIVE UPDATES",

    sources:
      "Sources:",

    githubReady:
      "GitHub Pages ready • No paid server required",

    warningText:
      "Warning",

    dangerText:
      "Danger",

    normal:
      "NORMAL",

    watch:
      "WATCH",

    active:
      "ACTIVE",

    officialAggregate:
      "Official aggregate not verified",

    monitoring:
      "DHM monitoring",

    forecastUnavailable:
      "DHM forecast not published",

    stationMonitoring:
      "DHM station monitoring available",

    rising:
      "Rising",

    falling:
      "Falling",

    stable:
      "Stable",

    unknown:
      "Unknown",

    rainUnit:
      "mm",

    meterUnit:
      "m"

  },


  ne: {

    title:
      "नेपाल बाढी २०२६ | प्रत्यक्ष अवस्था ड्यासबोर्ड",

    lastUpdated:
      "अन्तिम अपडेट",

    live:
      "प्रत्यक्ष",

    dataSource:
      "डेटा स्रोत: DHM • NDRRMA • नेपाल प्रहरी",

    maxRain:
      "अधिकतम २४ घण्टाको वर्षा",

    dhmRain:
      "DHM वर्षा निगरानी",

    maxRiver:
      "अधिकतम नदी सतह",

    warningStatus:
      "चेतावनी अवस्था",

    dhmWarning:
      "DHM चेतावनी प्रणाली",

    officialWarning:
      "आधिकारिक चेतावनी पृष्ठ",

    casualties:
      "मानवीय क्षति तथा प्रभाव",

    confirmedDeaths:
      "पुष्टि भएका<br>मृत्यु",

    missingPersons:
      "बेपत्ता<br>व्यक्ति",

    injuredPersons:
      "घाइते<br>व्यक्ति",

    damage:
      "पूर्वाधार क्षति",

    homesDamaged:
      "क्षतिग्रस्त<br>घर",

    bridgesDamaged:
      "क्षतिग्रस्त<br>पुल",

    damageNote:
      "आधिकारिक हालको कुल संख्या पुष्टि भएपछि मात्र देखाइन्छ।",

    riverLevels:
      "नदीको पानीको सतह",

    river:
      "नदी",

    current:
      "हाल",

    warning:
      "चेतावनी",

    danger:
      "खतरा",

    affectedAreas:
      "प्रभावित क्षेत्र — हालको DHM निगरानी",

    forecastNote:
      "DHM ले सम्बन्धित स्थानका लागि पूर्वानुमान प्रकाशित गरेको अवस्थामा मात्र देखाइन्छ। निगरानीको तथ्यलाई पूर्वानुमानको रूपमा देखाइएको छैन।",

    rescueRelief:
      "उद्धार तथा राहत कार्य",

    activeTeams:
      "सक्रिय टोली",

    peopleRescued:
      "उद्धार गरिएका व्यक्ति",

    rescueVehicles:
      "उद्धार सवारी",

    reliefDistributed:
      "वितरित राहत",

    operationsStatus:
      "कार्य सञ्चालन अवस्था",

    liveUpdates:
      "प्रत्यक्ष अपडेट",

    sources:
      "स्रोत:",

    githubReady:
      "GitHub Pages तयार • सशुल्क सर्भर आवश्यक छैन",

    warningText:
      "चेतावनी",

    dangerText:
      "खतरा",

    normal:
      "सामान्य",

    watch:
      "निगरानी",

    active:
      "सक्रिय",

    officialAggregate:
      "आधिकारिक कुल संख्या पुष्टि भएको छैन",

    monitoring:
      "DHM निगरानी",

    forecastUnavailable:
      "DHM पूर्वानुमान प्रकाशित भएको छैन",

    stationMonitoring:
      "DHM स्टेशन निगरानी उपलब्ध",

    rising:
      "बढ्दो",

    falling:
      "घट्दो",

    stable:
      "स्थिर",

    unknown:
      "अज्ञात",

    rainUnit:
      "मिमी",

    meterUnit:
      "मि"

  }

};


let currentLang =
  localStorage.getItem("nepalFloodLang") || "en";

let lightMode =
  localStorage.getItem("nepalFloodTheme") === "light";


/* ============================================================
   BASIC HELPERS
============================================================ */

function cleanNumber(value) {

  if (
    value === null ||
    value === undefined ||
    value === "" ||
    value === "—"
  ) {
    return null;
  }

  const number = Number(value);

  return Number.isFinite(number)
    ? number
    : null;
}


function safeString(value, fallback = "") {

  if (
    value === null ||
    value === undefined ||
    value === ""
  ) {
    return fallback;
  }

  return String(value);
}


function escapeHTML(value) {

  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");

}


/* ============================================================
   NUMBER FORMAT
============================================================ */

function fmt(value, decimals = 0) {

  const number = cleanNumber(value);

  if (number === null) {
    return "—";
  }

  return number.toLocaleString(
    currentLang === "ne"
      ? "ne-NP"
      : "en-US",
    {
      minimumFractionDigits: decimals,
      maximumFractionDigits: decimals
    }
  );

}


function unitText(unit) {

  if (unit === "mm") {
    return I18N[currentLang].rainUnit;
  }

  if (unit === "m") {
    return I18N[currentLang].meterUnit;
  }

  return unit;
}


function valueWithUnit(
  value,
  unit,
  decimals = 0
) {

  const number = cleanNumber(value);

  if (number === null) {
    return "—";
  }

  return `${fmt(number, decimals)} ${unitText(unit)}`;

}


/* ============================================================
   DATE + TIME
============================================================ */

function formatUpdated(value) {

  if (!value) {
    return "—";
  }

  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return safeString(value, "—");
  }

  const locale =
    currentLang === "ne"
      ? "ne-NP"
      : "en-GB";

  const formatter =
    new Intl.DateTimeFormat(
      locale,
      {
        timeZone: "Asia/Kathmandu",
        day: "2-digit",
        month: "short",
        year: "numeric",
        hour: "2-digit",
        minute: "2-digit",
        hour12: false
      }
    );

  const parts =
    formatter.formatToParts(date);

  const get = type =>
    parts.find(
      part => part.type === type
    )?.value || "";

  const day = get("day");
  const month = get("month");
  const year = get("year");
  const hour = get("hour");
  const minute = get("minute");

  if (currentLang === "ne") {

    return `${day} ${month} ${year} | ${hour}:${minute} NPT`;

  }

  return `${day} ${month} ${year} | ${hour}:${minute} NPT`;

}


/* ============================================================
   DATA NORMALIZATION
============================================================ */

function normalizeData(raw) {

  const source =
    raw &&
    typeof raw === "object"
      ? raw
      : {};

  const rainfall =
    source.rainfall ||
    source.rain ||
    {};

  const river =
    source.river ||
    {};

  const casualties =
    source.casualties ||
    {};

  const damage =
    source.damage ||
    {};

  const rescue =
    source.rescue ||
    source.operations ||
    {};


  let rivers =
    Array.isArray(source.rivers)
      ? source.rivers
      : [];


  rivers =
    rivers
      .filter(
        riverItem =>
          riverItem &&
          typeof riverItem === "object"
      )
      .map(
        riverItem => ({

          name:
            safeString(
              riverItem.name,
              "Unknown"
            ),

          basin:
            safeString(
              riverItem.basin,
              ""
            ),

          station:
            safeString(
              riverItem.station,
              "Unknown"
            ),

          water_level_m:
            cleanNumber(
              riverItem.water_level_m ??
              riverItem.value ??
              riverItem.level_m
            ),

          warning_level_m:
            cleanNumber(
              riverItem.warning_level_m ??
              riverItem.warning
            ),

          danger_level_m:
            cleanNumber(
              riverItem.danger_level_m ??
              riverItem.danger
            ),

          status:
            safeString(
              riverItem.status,
              "UNKNOWN"
            ),

          trend:
            safeString(
              riverItem.trend,
              "—"
            ),

          source:
            safeString(
              riverItem.source,
              "DHM River Watch"
            )

        })
      );


  let weather =
    Array.isArray(source.weather)
      ? source.weather
      : [];


  weather =
    weather
      .filter(
        item =>
          item &&
          typeof item === "object"
      )
      .map(
        item => ({

          place:
            safeString(
              item.place,
              "Unknown"
            ),

          value:
            cleanNumber(
              item.value ??
              item.rain_mm ??
              item.rainfall_mm
            ),

          note:
            safeString(
              item.note,
              ""
            )

        })
      );


  return {

    updated:
      source.updated_at ||
      source.updated_at_npt ||
      source.updated ||
      null,

    status:
      safeString(
        source.status,
        "LIVE"
      ),

    rainfall: {

      max_24h_mm:
        cleanNumber(
          rainfall.max_24h_mm ??
          rainfall.value ??
          source.max_24h_rainfall_mm
        ),

      station:
        safeString(
          rainfall.station,
          "—"
        ),

      source:
        safeString(
          rainfall.source,
          "DHM rainfall monitoring"
        )

    },

    river: {

      max_level_m:
        cleanNumber(
          river.max_level_m ??
          river.value ??
          source.max_river_level_m
        ),

      basin:
        safeString(
          river.basin,
          "—"
        ),

      station:
        safeString(
          river.station,
          "—"
        ),

      overall_warning:
        safeString(
          river.overall_warning,
          "NORMAL"
        )

    },

    rivers,

    casualties: {

      deaths:
        cleanNumber(
          casualties.deaths ??
          source.deaths
        ),

      missing:
        cleanNumber(
          casualties.missing ??
          source.missing
        ),

      injured:
        cleanNumber(
          casualties.injured ??
          source.injured
        )

    },

    damage: {

      homes:
        cleanNumber(
          damage.homes ??
          damage.homes_damaged ??
          source.homes
        ),

      bridges:
        cleanNumber(
          damage.bridges ??
          damage.bridges_damaged ??
          source.bridges
        )

    },

    rescue: {

      teams:
        cleanNumber(
          rescue.teams ??
          source.teams
        ),

      rescued:
        cleanNumber(
          rescue.rescued ??
          source.rescued
        ),

      vehicles:
        cleanNumber(
          rescue.vehicles ??
          source.vehicles
        ),

      relief:
        cleanNumber(
          rescue.relief ??
          source.relief
        )

    },

    weather,

    ticker:
      safeString(
        source.ticker,
        ""
      )

  };

}


/* ============================================================
   RIVER STATUS
============================================================ */

function riverStatus(river) {

  const level =
    cleanNumber(
      river.water_level_m
    );

  const warning =
    cleanNumber(
      river.warning_level_m
    );

  const danger =
    cleanNumber(
      river.danger_level_m
    );


  if (level === null) {
    return "UNKNOWN";
  }


  if (
    danger !== null &&
    level >= danger
  ) {
    return "DANGER";
  }


  if (
    warning !== null &&
    level >= warning
  ) {
    return "WARNING";
  }


  return "NORMAL";

}


function localizedRiverStatus(status) {

  const value =
    String(status || "")
      .toUpperCase();


  if (currentLang === "ne") {

    if (value === "DANGER") {
      return "खतरा";
    }

    if (value === "WARNING") {
      return "चेतावनी";
    }

    if (value === "NORMAL") {
      return "सामान्य";
    }

    return "अज्ञात";

  }


  return value;

}


function localizedTrend(value) {

  const trend =
    String(value || "")
      .toLowerCase();


  if (currentLang === "ne") {

    if (
      trend.includes("rising") ||
      trend.includes("increase")
    ) {
      return I18N.ne.rising;
    }

    if (
      trend.includes("falling") ||
      trend.includes("decrease")
    ) {
      return I18N.ne.falling;
    }

    if (trend.includes("stable")) {
      return I18N.ne.stable;
    }

    if (trend === "—") {
      return "—";
    }

    return I18N.ne.unknown;

  }


  return safeString(value, "—");

}


/* ============================================================
   LANGUAGE APPLICATION
============================================================ */

function applyLanguage() {

  document.documentElement.lang =
    currentLang === "ne"
      ? "ne"
      : "en";


  document
    .querySelectorAll("[data-i18n]")
    .forEach(node => {

      const key =
        node.dataset.i18n;

      const translated =
        I18N[currentLang][key];

      if (translated !== undefined) {
        node.innerHTML = translated;
      }

    });


  if (els.langToggle) {

    els.langToggle.textContent =
      currentLang === "en"
        ? "EN | ने"
        : "ने | EN";

  }


  render(
    window.__dashboardData ||
    normalizeData(FALLBACK)
  );

}


/* ============================================================
   THEME
============================================================ */

function applyTheme() {

  document.body.classList.toggle(
    "light",
    lightMode
  );


  if (els.themeIcon) {

    els.themeIcon.textContent =
      lightMode
        ? "☀"
        : "☾";

  }


  if (els.themeToggle) {

    els.themeToggle.setAttribute(
      "aria-label",
      lightMode
        ? "Switch to dark mode"
        : "Switch to light mode"
    );

  }

}


/* ============================================================
   WEATHER NOTE TRANSLATION
============================================================ */

function localizedWeatherNote(note, value) {

  if (value === null) {

    if (
      String(note)
        .toLowerCase()
        .includes("forecast")
    ) {
      return I18N[currentLang]
        .forecastUnavailable;
    }

    if (
      String(note)
        .toLowerCase()
        .includes("station")
    ) {
      return I18N[currentLang]
        .stationMonitoring;
    }

    return I18N[currentLang].unknown;

  }


  return currentLang === "ne"
    ? I18N.ne.monitoring
    : safeString(
        note,
        I18N.en.monitoring
      );

}


/* ============================================================
   TICKER
============================================================ */

function defaultTicker() {

  if (currentLang === "ne") {

    return "DHM का आधिकारिक चेतावनीहरू लागू छन्। यात्रा अघि स्थानीय अवस्था जाँच गर्नुहोस्। आपतकालीन बाढी सूचना: DHM टोल-फ्री ११५५।";

  }

  return "Official DHM warnings are in effect. Verify local conditions before travel. Emergency flood information: DHM toll-free 1155.";

}


/* ============================================================
   RENDER
============================================================ */

function render(rawData) {

  const data =
    normalizeData(rawData);


  window.__dashboardData =
    data;


  /* ----------------------------------------------------------
     UPDATED TIME
  ---------------------------------------------------------- */

  if (els.updated) {

    els.updated.textContent =
      formatUpdated(data.updated);

  }


  /* ----------------------------------------------------------
     RAINFALL
  ---------------------------------------------------------- */

  if (els.rainValue) {

    els.rainValue.textContent =
      valueWithUnit(
        data.rainfall.max_24h_mm,
        "mm",
        1
      );

  }


  if (els.rainStation) {

    els.rainStation.textContent =
      data.rainfall.station || "—";

  }


  /* ----------------------------------------------------------
     MAX RIVER
  ---------------------------------------------------------- */

  let maxRiver = null;


  data.rivers.forEach(river => {

    const level =
      cleanNumber(
        river.water_level_m
      );


    if (
      level !== null &&
      (
        !maxRiver ||
        level >
        maxRiver.water_level_m
      )
    ) {

      maxRiver = river;

    }

  });


  if (!maxRiver) {

    const fallbackLevel =
      cleanNumber(
        data.river.max_level_m
      );


    if (fallbackLevel !== null) {

      maxRiver = {

        name:
          data.river.basin || "River",

        station:
          data.river.station || "—",

        water_level_m:
          fallbackLevel,

        warning_level_m:
          null,

        danger_level_m:
          null

      };

    }

  }


  if (maxRiver) {

    if (els.riverValue) {

      els.riverValue.textContent =
        valueWithUnit(
          maxRiver.water_level_m,
          "m",
          1
        );

    }


    if (els.riverStation) {

      els.riverStation.textContent =
        `${safeString(maxRiver.name,"River")} River at ${safeString(maxRiver.station,"—")}`;

    }


    if (els.riverThreshold) {

      els.riverThreshold.textContent =
        `${I18N[currentLang].warningText}: ${
          valueWithUnit(
            maxRiver.warning_level_m,
            "m",
            1
          )
        } | ${
          I18N[currentLang].dangerText
        }: ${
          valueWithUnit(
            maxRiver.danger_level_m,
            "m",
            1
          )
        }`;

    }

  } else {

    if (els.riverValue) {
      els.riverValue.textContent = "—";
    }

    if (els.riverStation) {
      els.riverStation.textContent = "—";
    }

    if (els.riverThreshold) {

      els.riverThreshold.textContent =
        `${I18N[currentLang].warningText}: — | ${I18N[currentLang].dangerText}: —`;

    }

  }


  /* ----------------------------------------------------------
     WARNING STATUS
  ---------------------------------------------------------- */

  let warningActive = false;


  data.rivers.forEach(river => {

    const status =
      riverStatus(river);


    if (
      status === "WARNING" ||
      status === "DANGER"
    ) {

      warningActive = true;

    }

  });


  const overall =
    String(
      data.river.overall_warning || ""
    ).toUpperCase();


  if (
    overall === "WARNING" ||
    overall === "DANGER" ||
    overall === "ACTIVE"
  ) {

    warningActive = true;

  }


  if (els.warningStatus) {

    if (warningActive) {

      els.warningStatus.textContent =
        I18N[currentLang].active;

      els.warningStatus.className =
        "status red";

    } else {

      els.warningStatus.textContent =
        I18N[currentLang].normal;

      els.warningStatus.className =
        "status green";

    }

  }


  /* ----------------------------------------------------------
     CASUALTIES
  ---------------------------------------------------------- */

  if (els.deaths) {

    els.deaths.textContent =
      fmt(
        data.casualties.deaths
      );

  }


  if (els.missing) {

    els.missing.textContent =
      fmt(
        data.casualties.missing
      );

  }


  if (els.injured) {

    els.injured.textContent =
      fmt(
        data.casualties.injured
      );

  }


  /* ----------------------------------------------------------
     DAMAGE
  ---------------------------------------------------------- */

  if (els.homes) {

    els.homes.textContent =
      fmt(
        data.damage.homes
      );

  }


  if (els.bridges) {

    els.bridges.textContent =
      fmt(
        data.damage.bridges
      );

  }


  /* ----------------------------------------------------------
     RESCUE
  ---------------------------------------------------------- */

  if (els.teams) {

    els.teams.textContent =
      fmt(
        data.rescue.teams
      );

  }


  if (els.rescued) {

    els.rescued.textContent =
      fmt(
        data.rescue.rescued
      );

  }


  if (els.vehicles) {

    els.vehicles.textContent =
      fmt(
        data.rescue.vehicles
      );

  }


  if (els.relief) {

    els.relief.textContent =
      fmt(
        data.rescue.relief
      );

  }


  /* ----------------------------------------------------------
     RIVER TABLE
  ---------------------------------------------------------- */

  if (els.riverRows) {

    if (!data.rivers.length) {

      els.riverRows.innerHTML =
        `<tr>
          <td colspan="4">—</td>
        </tr>`;

    } else {

      els.riverRows.innerHTML =
        data.rivers
          .map(river => {

            const status =
              riverStatus(river);


            let trendClass =
              "trend";


            if (status === "DANGER") {
              trendClass = "t-red";
            }

            if (status === "WARNING") {
              trendClass = "t-yellow";
            }


            return `
              <tr>

                <td>
                  ${escapeHTML(river.name)}
                  <small>
                    (${escapeHTML(river.station)})
                  </small>

                  <br>

                  <span class="${trendClass}">
                    ${escapeHTML(
                      localizedTrend(river.trend)
                    )}
                  </span>

                </td>

                <td class="t-blue">
                  ${valueWithUnit(
                    river.water_level_m,
                    "m",
                    1
                  )}
                </td>

                <td class="t-yellow">
                  ${valueWithUnit(
                    river.warning_level_m,
                    "m",
                    1
                  )}
                </td>

                <td class="t-red">
                  ${valueWithUnit(
                    river.danger_level_m,
                    "m",
                    1
                  )}
                </td>

              </tr>
            `;

          })
          .join("");

    }

  }


  /* ----------------------------------------------------------
     WEATHER / AFFECTED AREAS
  ---------------------------------------------------------- */

  if (els.affectedWeather) {

    if (!data.weather.length) {

      els.affectedWeather.innerHTML =
        `<div class="forecast">
          <div class="place">—</div>
        </div>`;

    } else {

      els.affectedWeather.innerHTML =
        data.weather
          .map(weather => {

            const value =
              cleanNumber(
                weather.value
              );


            const note =
              localizedWeatherNote(
                weather.note,
                value
              );


            return `
              <div class="forecast">

                <div class="place">
                  ${escapeHTML(
                    weather.place
                  )}
                </div>

                <div class="weatherIcon">

                  <svg
                    viewBox="0 0 100 100"
                    fill="none"
                    aria-hidden="true">

                    <path
                      d="M25 60h49c9 0 16-7 16-16s-7-16-16-16c-2 0-4 .4-6 1.1C64 20 53 14 40 14c-14 0-25 9-28 22C6 37 3 42 3 48c0 7 6 12 13 12h9Z"
                      stroke="#36a7ff"
                      stroke-width="6"
                      stroke-linecap="round"
                      stroke-linejoin="round"/>

                    <path
                      d="M29 72l-5 12M50 72l-5 12M71 72l-5 12"
                      stroke="#36a7ff"
                      stroke-width="6"
                      stroke-linecap="round"/>

                  </svg>

                </div>

                <div class="rain">

                  ${
                    value === null
                      ? "—"
                      : valueWithUnit(
                          value,
                          "mm",
                          1
                        )
                  }

                </div>

                <div class="risk unknown">
                  ${escapeHTML(note)}
                </div>

              </div>
            `;

          })
          .join("");

    }

  }


  /* ----------------------------------------------------------
     OPERATIONS
  ---------------------------------------------------------- */

  const operationValues = [

    data.rescue.teams,
    data.rescue.rescued,
    data.rescue.vehicles,
    data.rescue.relief

  ];


  const hasOperations =
    operationValues.some(
      value =>
        cleanNumber(value) !== null
    );


  if (els.operationsStatus) {

    els.operationsStatus.textContent =
      hasOperations
        ? I18N[currentLang].monitoring
        : I18N[currentLang].officialAggregate;

  }


  if (els.operationsBar) {

    els.operationsBar.style.width =
      hasOperations
        ? "100%"
        : "0%";

  }


  /* ----------------------------------------------------------
     TICKER
  ---------------------------------------------------------- */

  if (els.ticker) {

    els.ticker.textContent =
      data.ticker ||
      defaultTicker();

  }

}


/* ============================================================
   DATA LOADING
============================================================ */

async function boot() {

  let data =
    normalizeData(FALLBACK);


  try {

    const response =
      await fetch(
        `data.json?ts=${Date.now()}`,
        {
          cache: "no-store"
        }
      );


    if (!response.ok) {

      throw new Error(
        `HTTP ${response.status}`
      );

    }


    const json =
      await response.json();


    data =
      normalizeData(json);


  } catch (error) {

    console.warn(
      "data.json could not be loaded. Using fallback data.",
      error
    );

  }


  render(data);

}


/* ============================================================
   LANGUAGE BUTTON
============================================================ */

els.langToggle?.addEventListener(
  "click",
  () => {

    currentLang =
      currentLang === "en"
        ? "ne"
        : "en";


    localStorage.setItem(
      "nepalFloodLang",
      currentLang
    );


    applyLanguage();

  }
);


/* ============================================================
   THEME BUTTON
============================================================ */

els.themeToggle?.addEventListener(
  "click",
  () => {

    lightMode =
      !lightMode;


    localStorage.setItem(
      "nepalFloodTheme",
      lightMode
        ? "light"
        : "dark"
    );


    applyTheme();

  }
);


/* ============================================================
   INITIALIZE
============================================================ */

applyTheme();

applyLanguage();

boot();


/* ============================================================
   AUTO REFRESH
============================================================ */

setInterval(
  boot,
  5 * 60 * 1000
);