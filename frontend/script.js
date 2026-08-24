const form = document.getElementById("registrationForm");
const message = document.getElementById("message");

form.addEventListener("submit", async function (event) {

    event.preventDefault();

    const name = document.getElementById("name").value.trim();
    const email = document.getElementById("email").value.trim();
    const mobile = document.getElementById("mobile").value.trim();

    if (!name || !email || !mobile) {

        showMessage(
            "Please fill all required fields.",
            "error"
        );

        return;
    }

    const selectedSkills = [];

    document
        .querySelectorAll('input[name="skills"]:checked')
        .forEach(function (checkbox) {

            selectedSkills.push(checkbox.value);

        });


    const registrationData = {

        name: name,

        email: email,

        mobile: mobile,

        city: document.getElementById("city").value.trim(),

        country: document.getElementById("country").value.trim(),

        company: document.getElementById("company").value.trim(),

        role: document.getElementById("role").value.trim(),

        experience: document.getElementById("experience").value,

        skills: selectedSkills,

        community: document.getElementById("community").value,

        comments: document.getElementById("comments").value.trim()
    };


    try {

        const response = await fetch(
            "/api/register",
            {
                method: "POST",

                headers: {
                    "Content-Type": "application/json"
                },

                body: JSON.stringify(registrationData)
            }
        );


        const result = await response.json();


        if (response.ok) {

            showMessage(
                result.message,
                "success"
            );

            form.reset();

        } else {

            showMessage(
                result.message,
                "error"
            );

        }

    } catch (error) {

        console.error(error);

        showMessage(
            "Unable to connect to the backend server.",
            "error"
        );

    }

});


function showMessage(text, type) {

    message.style.display = "block";

    message.textContent = text;

    if (type === "success") {

        message.style.backgroundColor = "#d1fae5";
        message.style.color = "#065f46";

    } else {

        message.style.backgroundColor = "#fee2e2";
        message.style.color = "#991b1b";

    }

}
