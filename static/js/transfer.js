
document.querySelector("form").addEventListener("submit", function (e) {
    e.preventDefault(); // Empêche le rechargement de la page

    const receiver = document.getElementById("receiver").value;
    const amount = document.getElementById("amount").value;
    const csrfToken = document.querySelector("[name=csrfmiddlewaretoken]").value;

    fetch("/accounts/transfer/", {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": csrfToken
        },
        body: JSON.stringify({ receiver: receiver, amount: amount })
    })
    .then(response => response.json())
    .then(data => {
        const message = document.createElement("p");
        message.textContent = data.message;
        message.style.color = data.success ? "green" : "red";
        document.body.appendChild(message);
    })
    .catch(error => console.error("Error:", error));
});
