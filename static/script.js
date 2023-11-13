document.addEventListener('DOMContentLoaded', myFunction)

function myFunction() {
    var checkBox = document.getElementById('terms');
    var text = document.getElementById('text');
    let register = document.getElementById('register')
    let formRegister = document.querySelector('form')

    checkBox.checked = false
    register.disabled = true
    document.addEventListener('click', function (){

        checkBox.onclick = function (){
            if (checkBox.checked === true){
                text.style.display = 'block';
                register.disabled = false
            } else {
               text.style.display = 'none';
               register.disabled = true
            }
        };

    })

    formRegister.onsubmit = function (){
        checkBox.checked = false
        register.disabled = true
    }
}
