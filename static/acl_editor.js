var tokens = []
var user_acl = {"member":{},"manager":{},"administrator":[]}

function add_member_permission(ico,new_permission) {
  member_keys = Object.keys(user_acl["member"]);
  if( member_keys.indexOf(ico) == -1 ) {
    user_acl.member[ico] = [new_permission];
    $("#select_permissions").append("<option value=\"" + new_permission + "\">" + new_permission + "</option>");
  }
  else {
    if( user_acl.member[ico].indexOf(new_permission) == -1 ) {
      user_acl.member[ico].push(new_permission);
      $("#select_permissions").append("<option value=\"" + new_permission + "\">" + new_permission + "</option>");
    }
  }
}

function remove_member_permission(ico,permission) {
  member_keys = Object.keys(user_acl["member"]);
  if( member_keys.indexOf(ico) != -1) {
    var removalIndex = user_acl.member[ico].indexOf(permission);
    if( removalIndex != -1 ) {
      delete user_acl.member[ico];
      $("#select_permissions option[value='"+permission+"']").remove();
    }
  }
}

function add_manager_permission(ico,new_permission) {
  manager_keys = Object.keys(user_acl["manager"]);
  if( manager_keys.indexOf(ico) == -1 ) {
    user_acl.manager[ico] = [new_permission];
    $("#select_permissions").append("<option value=\"" + new_permission + "\">" + new_permission + "</option>");
  }
  else {
    if( user_acl.manager[ico].indexOf(new_permission) == -1 ) {
      user_acl.manager[ico].push(new_permission);
      $("#select_permissions").append("<option value=\"" + new_permission + "\">" + new_permission + "</option>");
    }
  }
}

function remove_manager_permission(ico,permission) {
  manager_keys = Object.keys(user_acl["manager"]);
  if( manager_keys.indexOf(ico) != -1) {
    var removalIndex = user_acl.manager[ico].indexOf(permission);
    if( removalIndex != -1 ) {
      delete user_acl.manager[ico];
      $("#select_permissions option[value='"+permission+"']").remove();
    }
  }
}

function add_admin_permission(new_permission) {
  if( user_acl.administrator.indexOf(new_permission) == -1 ) {
    user_acl.administrator.push(new_permission);
    new_option = "<option value=\"" + new_permission;
    new_option += "\">" + new_permission + "</option>";
    $("#select_permissions").append(new_option);
  }
}

function remove_admin_permission(permission) {
  var removalIndex = user_acl.administrator.indexOf(permission);
  if( removalIndex != -1 ) {
    delete user_acl.administrator[removalIndex];
    $("#select_permissions option[value='"+permission+"']").remove();
  }
}

function show_member_permissions() {
  var selected_ico = $("select[name=member_ico]").val();
  $("#permissions_for").text(selected_ico + " - Member");
  $("#member").show();
  $("#manager").hide();
  $("#administrator").hide();
  $("#select_permissions").children("option").remove();
  current_acl = user_acl["member"][selected_ico];
  member_icos = Object.keys(user_acl["member"])
  if( member_icos.length > 0 ) {
    var selected_item = member_icos.indexOf(selected_ico);
    if( selected_item >= 0 ) {
      current_acl.forEach(function(element) {
        $("#select_permissions").append("<option>" + element + "</option");
      });
    }
  }
}

function show_manager_permissions() {
  var selected_ico = $("select[name=manager_ico]").val();
  $("#permissions_for").text(selected_ico + " - Manager");
  $("#member").hide();
  $("#manager").show();
  $("#administrator").hide();
  $("#select_permissions").children("option").remove();
  current_acl = user_acl["manager"][selected_ico];
  manager_icos = Object.keys(user_acl["manager"])
  if( manager_icos.length > 0 ) {
    var selected_item = manager_icos.indexOf(selected_ico);
    if( selected_item >= 0 ) {
      current_acl.forEach(function(element) {
        $("#select_permissions").append("<option>" + element + "</option");
      });
    }
  }
}

function show_admin_permissions() {
  $("#permissions_for").text("Administrator");
  $("#member").hide();
  $("#manager").hide();
  $("#administrator").show();
  $("#select_permissions").children("option").remove();
  user_acl["administrator"].forEach(function(element) {
    $("#select_permissions").append("<option value=\"" + element + "\">" + element + "</option");
  });
}

$(function(){
  tokens.forEach(function(element) {
    $("select[name=member_ico]").append("<option>" + element + "</option");
    $("select[name=manager_ico]").append("<option>" + element + "</option");
  });
  $("input[name=access_type]:radio").change(function(event){
    if( $(this).val() == "member" ){
      show_member_permissions();
    }
    else if( $(this).val() == "manager" ) {
      show_manager_permissions();
    }
    else {
      show_admin_permissions();
    }
  });
  $(".member_permission_checkbox").change(function(event){
    var permission = $(this).prop("name");
    var selected_ico = $("select[name=member_ico]").val();
    if( $(this).prop("checked") ) {
      add_member_permission(selected_ico,permission);
    }
    else {
      remove_member_permission(selected_ico,permission);
    }
  });
  $(".manager_permission_checkbox").change(function(event){
    var permission = $(this).prop("name");
    var selected_ico = $("select[name=manager_ico]").val();
    if( $(this).prop("checked") ) {
      add_manager_permission(selected_ico,permission);
    }
    else {
      remove_manager_permission(selected_ico,permission);
    }
  });
  $(".admin_permission_checkbox").change(function(event){
    var permission = $(this).prop("name");
    if( $(this).prop("checked") ) {
      add_admin_permission(permission);
    }else {
      remove_admin_permission(permission);
    }
  });
  $("select[name=manager_ico]").change(function() {
    $("#select_permissions").children("option").remove();
    var new_ico = $(this).val();
    var manager_keys = Object.keys(user_acl.manager);
    var index = manager_keys.indexOf(new_ico);
    if( index != -1 ) {
      $(".manager_permission_checkbox").each(function() {
        var element = $(this).prop("name");
        if( user_acl.manager[new_ico].indexOf(element) != -1 ) {
          $(this).prop("checked",true);
          $("#select_permissions").append("<option value=\"" + element + "\">" + element + "</option");
        }
        else {
          $(this).prop("checked",false);
        }
      });
    }
    else {
      $(".manager_permission_checkbox").prop("checked",false);
    }
  });
  $("select[name=member_ico]").change(function() {
    $("#select_permissions").children("option").remove();
    var new_ico = $(this).val();
    var member_keys = Object.keys(user_acl.member);
    var index = member_keys.indexOf(new_ico);
    if( index != -1 ) {
      $(".member_permission_checkbox").each(function() {
        var element = $(this).prop("name");
        if( user_acl.member[new_ico].indexOf(element) != -1 ) {
          $(this).prop("checked",true);
          $("#select_permissions").append("<option value=\"" + element + "\">" + element + "</option");
        }
        else {
          $(this).prop("checked",false);
        }
      });
    }
    else {
      $(".member_permission_checkbox").prop("checked",false);
    }
  });
  $("#view-acl-btn").click(function(){
    $("#view_acl").children().remove();
    $("#view_acl").append("<pre>" + JSON.stringify(user_acl,null,'\t') + "</pre>");
    $("#acl_manager").toggle();
    $("#view_acl").toggle();
    if ($("#view_acl").is(":visible")) {
      $(this).val("ACL Editor");
    }
    else {
      $(this).val("View Full ACL");
    }
  });
});
