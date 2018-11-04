$(function(){
    var full_name = $("input[name=full_name]");
    var email_address = $("input[name=email_address");
    var password = $("input[name=password");
    var password_repeat = $("input[name=password_repeat");

    $("#random_password_checkbox").change(function(event){
        var checked = $(this).prop("checked");
        if(checked) {
            password.val("");
            password_repeat.val("")
            password.prop("disabled",true);
            password_repeat.prop("disabled",true);
        }
        else {
            password.prop("disabled",false);
            password_repeat.prop("disabled",false);
        }
    });

    password.change(function (event) {
       if(password.val() != password_repeat.val()) {
           $("onboard_user_validation").text("Passwords do not match");
       }
    });
});