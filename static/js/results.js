function getResult(cb) {
  $.ajax({
    type: 'GET', 
    url: '/upload/check-task-status/',
    success: function(res) {
      if (cb(res) === 'incomplete') {
        // Poll the server every half second until a result is received
        setTimeout(getResult(checkResponseStatus), 500)
      }
    },
    error: function(res) {
      console.log('request failed')
    }
  });
};

// Poll the check_status view for progress on the load_infile task.
// Once the task is complete, render a sample of the data uploaded and, if
// necessary, any warnings that were returned. If the task fails, render an
// error message explaining why
function checkResponseStatus(res) {
    if (res.status == 'PROGRESS') {
      $('#progress-bar').css('width', (100 * res.result.current / res.result.total) + '%')
      $('#progress-message').html(res.result.message)
      return 'incomplete'
    }
    else if (res.status === 'SUCCESS') {
      $('#progress-bar').removeClass('active')
      // If a celery task ends its status is automatically SUCCESS, even if there
      // was an error.
      if (res.result.error) {
        $('#current-state').html('<span class="label label-danger">FAILURE</span>');
        $('#progress-message').html('Error')
        $('#message').html(`
          <div class="alert alert-danger sql-error">
            <p>
              <span class="glyphicon glyphicon-remove"></span>
              There was an error uploading to the database: </p>
            <p>
              ${res.result.errorMessage}
            </p>
            <p>
              <a href="/upload/" class="alert-link">Go back to the upload page</a>
            </p>
          </div>
        `)
        return
      }

      // If there isn't an error, fill the progress bar
      $('#progress-bar').css('width', '100%');
      $('#current-state').html('<span class="label label-success">SUCCESS</span>');
      $('#message').html(`
        <div class="alert alert-success">
          <p>
           <span class="glyphicon glyphicon-ok-circle"></span>
            Table <strong>${res.result.table}</strong> 
            was loaded into the <strong>imports</strong> database.</p>
          <p>
            <a href="/upload/" class="alert-link">Go back to the upload page</a>
          </p>
        </div>
      `)
      $('#progress-message').html('Finished')
      generateTable(res.result);

      // Append warnings
      if (res.result.warnings.length > 0) {
        warnings_html = res.result.warnings.map(function(w) {
          return `<li>${w}</li>`
        });
        $('#warnings').html(`<h2>Warnings</h2><ul>${warnings_html.join(' ')}</ul>`)
        $('#progress-message').html('Finished (with warnings)')

        $('#current-state').html('<span class="label label-warning">SUCCESS</span>');
        $('#message').html(`
          <div class="alert alert-warning">
            <p>
            <span class="glyphicon glyphicon-alert"></span>
            The upload succeeded, but there were <a href="#warnings" class="alert-link">warnings</a>.</p>
            <p><a href="/upload/" class="alert-link">Go back to the upload page</a></p>
          </div>
        `)
      }

      return;
    }
    else if (res.status == 'PENDING') {
      return 'incomplete';
    }
    else {
      $('#current-state').html('<span class="label label-danger">FAILURE</span>');
      $('#progress-bar').removeClass('active')
      $('#details').html(res.result)
      return;
    }
}

// Create a table with sample data
function generateTable(res) {
  var rowData = res.data.slice(1)
  var headerData = res.data[0]

  var headers = headerData.map(function(header, i) {
    return (`
      <th>
        ${header}
        <span class="sql-type">${res.headers[i]['raw_type']}</span>
      </th>
    `)
  });

  var rows = rowData.map(function(row, i) {
    var cells = row.map(function(cell) {
        return `<td>${cell}</td>`
    });

    return `<tr>${cells.join('')}</tr>`
  });

  var markup = `
    <div class="small">Sample data; Not all rows may be shown</div>
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
