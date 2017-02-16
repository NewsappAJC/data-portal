/* global $ */

window.onload = function() {
  addUploadHandler(ajaxPost);
}

function next(data) {
  window.location.href = '/upload/categorize';
}

function showModal(data) {
  data.headers.forEach(function(h) {
    $('#header-input-holder').append('<li>' + h + '</li>');
  });
  // Add event handler to the continue button in the modal
  $('#continue-btn').on('click', function(e) {
    e.preventDefault();
    e.stopPropagation();
    $('#metadata-form').show();
    $('#header-prompt').hide();

    // Change the event handler on the button
    $(this).on('click', function(e) {
      e.preventDefault();
      e.stopPropagation();
      var data = new FormData($('#metadata-form')[0]);
      ajaxPost('/upload/add-metadata/', data, next)
    })
  });
  $('#headerModal').modal();
}


// Event handler for submit button
function addUploadHandler(callback) {
  $('#file-submit').on('click', function(e) {
    e.preventDefault();
    e.stopPropagation();
    // Get the data from the form and send it as an AJAX post request
    var data = new FormData($('#upload-form')[0]);
    callback('/upload/upload-file/', data, showModal);

    // Defined as a global so that we can enable/disable from within multiple
    // functions
    $btn = $(this).button('loading');
  });
  return;
}


function ajaxPost(url, data, callback) {
  $.ajax({
    url: url,
    type: 'POST', 
    contentType: false,
    processData: false,
    cache: false,
    // We have to add a CSRF token as a header or Django will complain
    headers: {'X-CSRFToken': data.get('csrfmiddlewaretoken')},
    data: data,
    success: function(res) {
      // Redirect to the categorize page if form validates and upload to S3
      // succeeds
      callback(res);
    },
    error: function(res) {
      addErrorMessages(JSON.parse(res.responseJSON));
      $btn.button('reset');
    }
  });
};

function addErrorMessages(errors) {
  // Clear existing errors
  $('.errors').each(function() {
    $(this).html('');
  });

  // Loop through errors
  $.each(errors, function(err) {
    messages = errors[err]
    // We're only interested in the messages for each error
    fmessages = messages.map(function(m) {
      return m.message;
    });

    // Some errors aren't linked to any particular field
    if  (err === '__all__') {
      $('#non-field-errors').text(fmessages.join(', '));
    }
    else {
      // Append error messages specified for different field
      var field = $('#id_' + err);
      errorDiv = field.siblings()[0];
      $(errorDiv).text(fmessages.join(', ')); // Use text instead of HTML to prevent XSS
    };
  });
};
