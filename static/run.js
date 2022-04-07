// Show analyze tweets pop-up
const showPopup = function() {
    document.getElementById("pop-up-blocker").classList.remove("hide");
}

// Courtesy of https://www.codegrepper.com/code-examples/javascript/settimeout+infinite+loop
const sleep = (milliseconds) => {
    return new Promise(resolve => setTimeout(resolve, milliseconds))
}

window.onload = async function() {
    // Set up close button for search pop-up
    document.getElementById("close-pop-up").addEventListener("click", function() {
        document.getElementById("pop-up-blocker").classList.add("hide");
    });

    // Set up close button for errors
    const errors = document.getElementById("errors");
    if (errors != null) {
        document.getElementById("close-errors").addEventListener("click", function() {
            errors.classList.add("hide");
        });
    }

    // AJAX for the Tweet Workshop, courtesy of the mini-lesson
    var xhttp = new XMLHttpRequest();
    const displayClass = document.getElementById("displayClass");

    xhttp.onreadystatechange = function() {
        //if we're actually done successfully
        if (this.readyState == 4 && this.status == 200) {
            let tweetClass = "";
            let color = "";
            
            // Check which response was given
            document.getElementById("workshop-loading").classList.add("hide");
            if (this.responseText.substring(1, 2) == "C") {
                tweetClass = "Cool!";
                color = "#41FF7A";
            } else if (this.responseText.substring(1, 6) == "NMCOT") {
                tweetClass = "Not My Cup Of Tea";
                color = "#FF5151";
            } else {
                tweetClass = "Could Not Determine";
                color = "#f0ff1f"
            }

            // Change classification text and color
            displayClass.innerHTML = tweetClass;
            displayClass.style.color = color;
        }
    };

    // Keep sending AJAX requests every second
    while (true) {
        let tweetText = document.getElementById("workshop-text").value;

        if (tweetText.length > 0) // If user is interacting with workshop
        {
            document.getElementById("workshop-loading").classList.remove("hide");
            xhttp.open("POST", "/classifyTweet", true);
            xhttp.send(tweetText); //asynchronous request
        } else {
            displayClass.innerHTML = "None";
            displayClass.style.color = "black";
        }
        await sleep(1000);
    }
}
