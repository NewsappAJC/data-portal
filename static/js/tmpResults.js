var csrf;

// Get data from form
$('#file-submit').on('click', function() {

  // Get the date from the form and post it
  var data = new FormData($('#upload-form')[0]);
  csrf = data.get('csrfmiddlewaretoken');
  postForm(data);

  var $btn = $(this).button('loading');
});

function postForm(data) {
  $.ajax({
    url: '/',
    type: 'POST', 
    contentType: false,
    processData: false,
    cache: false,
    headers: {'X-CSRFToken': csrf},
    data: data,
    success: function(res) {
      window.location.href = '/categorize/';
    },
    error: function(res) {
      console.log('request failed')
    }
  });
};

