window.initLoginForm = function () {
    console.log("initLoginForm loaded");

    const form = document.getElementById("loginForm");
    const errorBox = document.getElementById("error");

    if (!form) {
        console.error("loginForm NOT FOUND");
        return;
    }

    form.addEventListener("submit", async function (e) {
        e.preventDefault();

        errorBox.classList.add("d-none");

        const username = document.getElementById("username").value;
        const password = document.getElementById("password").value;

        const response = await fetch("/api/auth/login", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ username, password })
        });

        if (!response.ok) {
            errorBox.textContent = "Utilizator sau parola incorecta!";
            errorBox.classList.remove("d-none");
            return;
        }

        const data = await response.json();
        sessionStorage.setItem("token", data.token);
        window.location.href = "/";
    });
};
