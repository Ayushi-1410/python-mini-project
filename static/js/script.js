document.addEventListener("DOMContentLoaded", () => {
    const themeToggle = document.querySelector("#theme-toggle");
    const savedTheme = localStorage.getItem("patient-queue-theme");
    const setTheme = (theme) => {
        document.documentElement.dataset.theme = theme;
        if (themeToggle) {
            const darkMode = theme === "dark";
            themeToggle.setAttribute("aria-pressed", String(darkMode));
            themeToggle.setAttribute("aria-label", `Switch to ${darkMode ? "light" : "dark"} mode`);
            themeToggle.querySelector(".theme-icon").textContent = darkMode ? "☀" : "☾";
            themeToggle.querySelector(".theme-label").textContent = darkMode ? "Light mode" : "Dark mode";
        }
    };

    setTheme(savedTheme === "dark" ? "dark" : "light");
    themeToggle?.addEventListener("click", () => {
        const nextTheme = document.documentElement.dataset.theme === "dark" ? "light" : "dark";
        localStorage.setItem("patient-queue-theme", nextTheme);
        setTheme(nextTheme);
    });

    const patientForm = document.querySelector("#patient-form");

    if (patientForm) {
        const requiredFields = ["patient_name", "age", "gender", "department", "symptoms"];

        patientForm.addEventListener("submit", (event) => {
            let firstInvalidField = null;

            for (const fieldName of requiredFields) {
                const field = patientForm.elements[fieldName];
                const error = field.closest(".form-field").querySelector(".field-error");
                let message = "";

                if (!field.value.trim()) {
                    message = "This field is required.";
                } else if (fieldName === "age" && (!/^\d+$/.test(field.value) || Number(field.value) < 1 || Number(field.value) > 120)) {
                    message = "Enter a whole number from 1 to 120.";
                }

                field.setAttribute("aria-invalid", message ? "true" : "false");
                error.textContent = message;
                if (message && firstInvalidField === null) {
                    firstInvalidField = field;
                }
            }

            const contact = patientForm.elements.contact_number;
            const contactError = contact.closest(".form-field").querySelector(".field-error");
            const contactValue = contact.value.trim();
            const contactDigits = (contactValue.match(/[0-9]/g) || []).length;
            const validContact = !contactValue || (contactValue.length <= 30 && /^\+?[0-9() -]+$/.test(contactValue) && contactDigits >= 7 && contactDigits <= 15);
            const contactMessage = validContact ? "" : "Enter a valid contact number, or leave it blank.";
            contact.setAttribute("aria-invalid", contactMessage ? "true" : "false");
            contactError.textContent = contactMessage;
            if (contactMessage && firstInvalidField === null) {
                firstInvalidField = contact;
            }

            const priority = patientForm.querySelector("input[name='priority_level']:checked");
            const priorityError = patientForm.querySelector("[data-error-for='priority_level']");
            priorityError.textContent = priority ? "" : "Select a staff-assigned priority.";

            if (firstInvalidField || !priority) {
                event.preventDefault();
                if (firstInvalidField) {
                    firstInvalidField.focus();
                } else {
                    patientForm.querySelector("input[name='priority_level']").focus();
                }
            }
        });

        patientForm.addEventListener("input", (event) => {
            if (event.target.matches("input, textarea, select") && event.target.getAttribute("aria-invalid") === "true") {
                event.target.removeAttribute("aria-invalid");
                const error = event.target.closest(".form-field")?.querySelector(".field-error");
                if (error) {
                    error.textContent = "";
                }
            }
        });
    }

    document.querySelectorAll(".status-form").forEach((form) => {
        form.addEventListener("submit", (event) => {
            const status = form.elements.status.value;
            if (status === "Completed" && !window.confirm("Mark this visit as completed?")) {
                event.preventDefault();
            }
        });
    });

    document.querySelectorAll("input[name='priority_level']").forEach((radio) => {
        radio.addEventListener("change", () => {
            const priorityError = document.querySelector("[data-error-for='priority_level']");
            if (priorityError) {
                priorityError.textContent = "";
            }
        });
    });
});
