// Constants
var c = 0;

function getResult(cb) {
  $.ajax({
    type: 'GET', 
    url: '/check-task-status/',
    success: function(res) {
      c++;
      if (cb(res) == 'incomplete') {
        if (c < 50) {
          console.log('trying...')
          setTimeout(getResult(checkResponseStatus), 500)
        }
      }
    },
    error: function(res) {
      console.log('request failed')
    }
  });
};

function checkResponseStatus(res) {
    console.log(res)
    if (res.status == 'PROGRESS') {
      $('#progress-bar').css('width', (100 * res.result.current / res.result.total) + '%')
      $('#progress-message').html(res.result.message)
      return 'incomplete'
    }
    else if (res.status === 'SUCCESS') {
      if (res.result.error) {
        $('#current-state').html('<span class="label label-danger">FAILURE</span>');
        $('#progress-message').html('Error')
        $('#message').html(`
          <div class="alert alert-danger sql-error">
            <p>There was an error uploading to the database: </p>
            <p>
              ${res.result.errorMessage}
            </p>
            <p>
              <a href="/" class="alert-link">Go back to the upload form</a>
            </p>
          </div>
        `)
        return
      }

      $('#progress-bar').css('width', '100%');
      $('#current-state').html('<span class="label label-success">SUCCESS</span>');
      $('#message').html(`
        <div class="alert alert-success">
          <p>
            <a href="/" class="alert-link">Go back to the upload form</a>
          </p>
        </div>
      `)
      $('#progress-message').html('Finished')
      generateTable(res.result);

      if (res.result.warnings.length > 0) {
        warnings_html = res.result.warnings.map(function(w) {
          return `<li>${w}</li>`
        });
        $('#warnings').html(`<h2>Warnings</h2><ul>${warnings_html.join(' ')}</ul>`)
        $('#progress-message').html('Finished (with warnings)')

        $('#current-state').html('<span class="label label-warning">SUCCESS</span>');
        $('#message').html(`
          <div class="alert alert-warning">
            <p>The upload succeeded, but there were <a href="#warnings" class="alert-link">warnings</a>.</p>
            <p><a href="/" class="alert-link">Go back to the upload form</a></p>
          </div>
        `)
      }

      return;
    }
    else if (res.status == 'PENDING') {
      return
    }
    else {
      $('#current-state').html('<span class="label label-danger">FAILURE</span>');
      $('#details').html(res.result)
      return;
    }
}

function generateTable(res) {
  var rowData = res.data.slice(1)
  var headerData = res.data[0]

  var headers = headerData.map(function(header, i) {
      return `<th>${header}</th>`
  });

  var rows = rowData.map(function(row, i) {
    var cells = row.map(function(cell) {
        return `<td>${cell}</td>`
    });

    return `<tr>${cells.join('')}</tr>`
  });

  var markup = `
    <table class="table table-striped">
      <thead>
        <tr>${headers.join('')}</tr>
      </thead>
      <tbody>
        ${rows.join('')}
      </tbody>
    </table>
  `;

  $('#details').html(markup)
}

getResult(checkResponseStatus);
