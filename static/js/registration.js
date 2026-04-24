document.addEventListener("DOMContentLoaded", () => {
    const form = document.querySelector("form");
    if (!form) return;

    form.addEventListener("submit", (e) => {
        const pwd = form.querySelector('input[name="password"]');
        const email = form.querySelector('input[name="email"]');
        const name = form.querySelector('input[name="name"]');

        if (!name.value.trim()) {
            alert("Name is required.");
            e.preventDefault();
            return;
        }

        if (!email.value.includes("@")) {
            alert("Please enter a valid email.");
            e.preventDefault();
            return;
        }

        if (pwd.value.length < 4) {
            alert("Password should be at least 4 characters.");
            e.preventDefault();
            return;
        }
    });
});