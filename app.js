const $ = (selector) => {
  return document.querySelector(selector);
};


function showToast(message) {

  const toast = $("#toast");

  toast.textContent = message;

  toast.classList.add("show");

  clearTimeout(window.__toastTimer);

  window.__toastTimer = setTimeout(() => {

    toast.classList.remove("show");

  }, 1800);
}


async function loadData() {

  try {

    const response = await fetch(
      "data.json",
      {
        cache: "no-store"
      }
    );

    if (!response.ok) {
      throw new Error("Could not load data.json");
    }


    const data = await response.json();


    /*
     * Update timestamp
     */

    if (data.last_updated) {

      const date = new Date(
        data.last_updated
      );

      const formatted =
        date.toLocaleString(
          "en-IN",
          {
            dateStyle: "medium",
            timeStyle: "short",
            hour12: true,
            timeZone: "Asia/Kathmandu"
          }
        );

      $("#updatedAt").textContent =
        formatted.replace(
          " at ",
          " • "
        ) + " NPT";
    }


    /*
     * Update statistics
     */

    const values = [

      [
        "#deaths",
        data.stats?.deaths?.value
      ],

      [
        "#missing",
        data.stats?.missing?.value
      ],

      [
        "#rescued",
        data.stats?.rescued?.value
      ],

      [
        "#affected",
        data.stats?.affected_population?.value
      ]

    ];


    values.forEach(
      ([selector, value]) => {

        if (
          value !== undefined &&
          value !== null
        ) {

          $(selector).textContent =
            typeof value === "number"
              ? value.toLocaleString("en-IN")
              : value;
        }

      }
    );


  } catch (error) {

    /*
     * Keep the dashboard's existing
     * snapshot if live data cannot load.
     */

    console.info(
      "Using bundled dashboard snapshot."
    );

  }

}


/*
 * Button actions
 */

document
  .querySelectorAll("[data-action]")
  .forEach((button) => {

    button.addEventListener(
      "click",
      () => {

        const action =
          button.dataset.action || "dashboard";

        const name =
          action.charAt(0).toUpperCase() +
          action.slice(1);

        showToast(
          `${name} section is ready.`
        );

      }
    );

  });


/*
 * Load data immediately.
 */

loadData();


/*
 * Refresh the dashboard data every
 * 45 seconds.
 */

setInterval(
  loadData,
  45000
); 
