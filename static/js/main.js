async function sendUsername() {
    const user = document.querySelector('#user').value;

    fetch('/set/username/', {
        method: 'POST',
        body: JSON.stringify({ username: user }),
        cache: 'no-cache',
        headers: new Headers({
            'content-type': 'application/json'
        })
    })
        .then(response => {
            if (response.status !== 200) {
                console.log(`Status problem: ${response.status}`);
                return;
            }
        })
        .catch(error => {
            console.log('Error', error)
        });
}

