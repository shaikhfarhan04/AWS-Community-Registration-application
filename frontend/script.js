const form = document.getElementById("registrationForm");
const message = document.getElementById("message");

form.addEventListener("submit", function (event) {

    event.preventDefault();

    const name = document.getElementById("name").value.trim();
    const email = document.getElementById("email").value.trim();
    const mobile = document.getElementById("mobile").value.trim();

    if (!name || !email || !mobile) {

        message.style.display = "block";
        message.textContent = "Please fill all required fields.";

        return;
    }

    const selectedSkills = [];

    document
        .querySelectorAll('input[name="skills"]:checked')
        .forEach(function (checkbox) {

            selectedSkills.push(checkbox.value);

        });

    console.log("Registration Data:");

    console.log({
        name: name,
        email: email,
        mobile: mobile,
        skills: selectedSkills
    });

    message.style.display = "block";
    message.textContent =
        "Registration form submitted successfully!";

    form.reset();
});