/**
 * Doctor Dashboard functionality for Medical Portal
 * Provides patient management, appointment handling, and medical record features
 */

document.addEventListener('DOMContentLoaded', function() {
  // Initialize components
  initAppointmentCalendar();
  initPatientSearch();
  initTaskManagement();
  setupEventListeners();
  equalizeCardHeights();
  
  // Re-equalize card heights when window is resized
  window.addEventListener('resize', debounce(equalizeCardHeights, 200));
  
  /**
   * Initialize the appointment calendar
   */
  function initAppointmentCalendar() {
    const appointmentCalendar = document.getElementById('appointment-calendar');
    if (!appointmentCalendar) return;
    
    // Check if FullCalendar is loaded
    if (typeof FullCalendar === 'undefined') {
      console.warn('FullCalendar is not loaded. Calendar initialization skipped.');
      return;
    }
    
    // Get the calendar data from the data attribute
    const calendarData = JSON.parse(appointmentCalendar.dataset.appointments || '[]');
    
    // Initialize FullCalendar
    const calendar = new FullCalendar.Calendar(appointmentCalendar, {
      initialView: 'timeGridDay',
      headerToolbar: {
        left: 'prev,next today',
        center: 'title',
        right: 'dayGridMonth,timeGridWeek,timeGridDay,listWeek'
      },
      height: 'auto',
      navLinks: true,
      editable: false,
      selectable: true,
      nowIndicator: true,
      dayMaxEvents: true,
      slotMinTime: '08:00:00',
      slotMaxTime: '20:00:00',
      slotDuration: '00:15:00',
      events: calendarData,
      eventTimeFormat: {
        hour: '2-digit',
        minute: '2-digit',
        meridiem: 'short'
      },
      eventClick: function(info) {
        showAppointmentDetails(info.event);
      },
      dateClick: function(info) {
        // Only allow creating events in day or week view
        if (calendar.view.type === 'timeGridDay' || calendar.view.type === 'timeGridWeek') {
          showAppointmentCreationModal(info.date);
        }
      },
      eventContent: function(arg) {
        // Customize event appearance
        const event = arg.event;
        const status = event.extendedProps.status;
        const eventEl = document.createElement('div');
        eventEl.className = 'fc-event-content p-1';
        
        const timeEl = document.createElement('div');
        timeEl.className = 'text-xs font-medium';
        timeEl.innerHTML = arg.timeText;
        
        const titleEl = document.createElement('div');
        titleEl.className = 'font-medium';
        titleEl.innerHTML = event.title;
        
        const patientEl = document.createElement('div');
        patientEl.className = 'text-xs';
        patientEl.innerHTML = event.extendedProps.patient || '';
        
        // Add status indicator
        const statusEl = document.createElement('div');
        statusEl.className = 'inline-block w-2 h-2 rounded-full mr-1';
        
        if (status === 'confirmed') {
          statusEl.classList.add('bg-green-500');
        } else if (status === 'pending') {
          statusEl.classList.add('bg-yellow-500');
        } else if (status === 'cancelled') {
          statusEl.classList.add('bg-red-500');
        } else if (status === 'completed') {
          statusEl.classList.add('bg-blue-500');
        } else {
          statusEl.classList.add('bg-gray-500');
        }
        
        titleEl.prepend(statusEl);
        
        eventEl.appendChild(timeEl);
        eventEl.appendChild(titleEl);
        eventEl.appendChild(patientEl);
        
        return { domNodes: [eventEl] };
      }
    });
    
    calendar.render();
    
    // Store calendar instance for access in other functions
    window.doctorCalendar = calendar;
  }
  
  /**
   * Show appointment details modal
   */
  function showAppointmentDetails(event) {
    // Get appointment data
    const appointmentId = event.id;
    const title = event.title;
    const start = event.start;
    const end = event.end;
    const patientName = event.extendedProps.patient;
    const patientId = event.extendedProps.patientId;
    const status = event.extendedProps.status;
    const type = event.extendedProps.type;
    const notes = event.extendedProps.notes || '';
    
    // Create modal
    const modal = document.createElement('div');
    modal.className = 'fixed inset-0 z-50 overflow-y-auto';
    modal.innerHTML = `
      <div class="flex items-center justify-center min-h-screen px-4 pt-4 pb-20 text-center sm:block sm:p-0">
        <div class="fixed inset-0 transition-opacity" aria-hidden="true">
          <div class="absolute inset-0 bg-gray-500 opacity-75"></div>
        </div>
        <span class="hidden sm:inline-block sm:align-middle sm:h-screen" aria-hidden="true">&#8203;</span>
        <div class="inline-block align-bottom bg-white rounded-lg text-left overflow-hidden shadow-xl transform transition-all sm:my-8 sm:align-middle sm:max-w-lg sm:w-full">
          <div class="bg-white px-4 pt-5 pb-4 sm:p-6 sm:pb-4">
            <div class="sm:flex sm:items-start">
              <div class="mt-3 text-center sm:mt-0 sm:ml-4 sm:text-left w-full">
                <h3 class="text-lg leading-6 font-medium text-gray-900 flex items-center">
                  <span class="inline-block w-3 h-3 rounded-full mr-2 ${
                    status === 'confirmed' ? 'bg-green-500' : 
                    status === 'pending' ? 'bg-yellow-500' : 
                    status === 'cancelled' ? 'bg-red-500' : 
                    status === 'completed' ? 'bg-blue-500' : 'bg-gray-500'
                  }"></span>
                  Appointment Details
                </h3>
                <div class="mt-4 space-y-3">
                  <div>
                    <p class="text-sm text-gray-500">Appointment Type</p>
                    <p class="font-medium">${type}</p>
                  </div>
                  <div>
                    <p class="text-sm text-gray-500">Patient</p>
                    <p class="font-medium">${patientName}</p>
                  </div>
                  <div class="grid grid-cols-2 gap-4">
                    <div>
                      <p class="text-sm text-gray-500">Date</p>
                      <p class="font-medium">${start.toLocaleDateString()}</p>
                    </div>
                    <div>
                      <p class="text-sm text-gray-500">Time</p>
                      <p class="font-medium">${start.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})} - ${end.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}</p>
                    </div>
                  </div>
                  <div>
                    <p class="text-sm text-gray-500">Status</p>
                    <p class="font-medium">${status.charAt(0).toUpperCase() + status.slice(1)}</p>
                  </div>
                  <div>
                    <p class="text-sm text-gray-500">Notes</p>
                    <p class="font-medium">${notes || 'No notes available'}</p>
                  </div>
                </div>
              </div>
            </div>
          </div>
          <div class="bg-gray-50 px-4 py-3 sm:px-6 sm:flex sm:flex-row-reverse">
            ${status !== 'completed' && status !== 'cancelled' ? `
              <button type="button" class="start-appointment-btn w-full inline-flex justify-center rounded-md border border-transparent shadow-sm px-4 py-2 bg-blue-600 text-base font-medium text-white hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 sm:ml-3 sm:w-auto sm:text-sm" data-appointment-id="${appointmentId}">
                Start Appointment
              </button>
            ` : ''}
            ${status !== 'completed' && status !== 'cancelled' ? `
              <button type="button" class="cancel-appointment-btn w-full inline-flex justify-center rounded-md border border-transparent shadow-sm px-4 py-2 bg-red-600 text-base font-medium text-white hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500 sm:ml-3 sm:w-auto sm:text-sm" data-appointment-id="${appointmentId}">
                Cancel
              </button>
            ` : ''}
            <a href="/patients/${patientId}/" class="w-full inline-flex justify-center rounded-md border border-gray-300 shadow-sm px-4 py-2 bg-white text-base font-medium text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 sm:ml-3 sm:w-auto sm:text-sm">
              View Patient Profile
            </a>
            <button type="button" class="close-modal-btn mt-3 w-full inline-flex justify-center rounded-md border border-gray-300 shadow-sm px-4 py-2 bg-white text-base font-medium text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 sm:mt-0 sm:ml-3 sm:w-auto sm:text-sm">
              Close
            </button>
          </div>
        </div>
      </div>
    `;
    
    // Add to document
    document.body.appendChild(modal);
    
    // Add event listeners
    modal.querySelector('.close-modal-btn').addEventListener('click', function() {
      modal.remove();
    });
    
    // Close when clicking outside the modal
    modal.addEventListener('click', function(e) {
      if (e.target === modal) {
        modal.remove();
      }
    });
    
    // Start appointment button
    const startAppointmentBtn = modal.querySelector('.start-appointment-btn');
    if (startAppointmentBtn) {
      startAppointmentBtn.addEventListener('click', function() {
        window.location.href = `/appointments/${appointmentId}/start/`;
      });
    }
    
    // Cancel appointment button
    const cancelAppointmentBtn = modal.querySelector('.cancel-appointment-btn');
    if (cancelAppointmentBtn) {
      cancelAppointmentBtn.addEventListener('click', function() {
        if (confirm('Are you sure you want to cancel this appointment?')) {
          cancelAppointment(appointmentId, modal);
        }
      });
    }
  }
  
  /**
   * Show appointment creation modal
   */
  function showAppointmentCreationModal(date) {
    // Format date and time
    const formattedDate = date.toISOString().split('T')[0];
    const hours = date.getHours().toString().padStart(2, '0');
    const minutes = Math.floor(date.getMinutes() / 15) * 15; // Round to nearest 15 min
    const formattedTime = `${hours}:${minutes.toString().padStart(2, '0')}`;
    
    // Get CSRF token
    const csrfToken = document.querySelector('meta[name="csrf-token"]').getAttribute('content');
    
    // Create modal
    const modal = document.createElement('div');
    modal.className = 'fixed inset-0 z-50 overflow-y-auto';
    modal.innerHTML = `
      <div class="flex items-center justify-center min-h-screen px-4 pt-4 pb-20 text-center sm:block sm:p-0">
        <div class="fixed inset-0 transition-opacity" aria-hidden="true">
          <div class="absolute inset-0 bg-gray-500 opacity-75"></div>
        </div>
        <span class="hidden sm:inline-block sm:align-middle sm:h-screen" aria-hidden="true">&#8203;</span>
        <div class="inline-block align-bottom bg-white rounded-lg text-left overflow-hidden shadow-xl transform transition-all sm:my-8 sm:align-middle sm:max-w-lg sm:w-full">
          <form id="create-appointment-form">
            <div class="bg-white px-4 pt-5 pb-4 sm:p-6 sm:pb-4">
              <div class="sm:flex sm:items-start">
                <div class="mt-3 text-center sm:mt-0 sm:ml-4 sm:text-left w-full">
                  <h3 class="text-lg leading-6 font-medium text-gray-900">
                    Create New Appointment
                  </h3>
                  <div class="mt-4 space-y-4">
                    <div>
                      <label for="patient" class="block text-sm font-medium text-gray-700">Patient</label>
                      <div class="mt-1">
                        <input type="text" name="patient_search" id="patient-search" class="shadow-sm focus:ring-blue-500 focus:border-blue-500 block w-full sm:text-sm border-gray-300 rounded-md" placeholder="Search for a patient...">
                        <div id="patient-search-results" class="hidden absolute z-10 mt-1 w-full bg-white shadow-lg rounded-md overflow-hidden"></div>
                        <input type="hidden" name="patient_id" id="patient-id">
                      </div>
                    </div>
                    <div>
                      <label for="appointment_type" class="block text-sm font-medium text-gray-700">Appointment Type</label>
                      <div class="mt-1">
                        <select name="appointment_type" id="appointment-type" class="shadow-sm focus:ring-blue-500 focus:border-blue-500 block w-full sm:text-sm border-gray-300 rounded-md">
                          <option value="consultation">Consultation</option>
                          <option value="follow_up">Follow-up</option>
                          <option value="examination">Examination</option>
                          <option value="procedure">Procedure</option>
                          <option value="other">Other</option>
                        </select>
                      </div>
                    </div>
                    <div class="grid grid-cols-2 gap-4">
                      <div>
                        <label for="appointment_date" class="block text-sm font-medium text-gray-700">Date</label>
                        <div class="mt-1">
                          <input type="date" name="appointment_date" id="appointment-date" class="shadow-sm focus:ring-blue-500 focus:border-blue-500 block w-full sm:text-sm border-gray-300 rounded-md" value="${formattedDate}">
                        </div>
                      </div>
                      <div>
                        <label for="appointment_time" class="block text-sm font-medium text-gray-700">Time</label>
                        <div class="mt-1">
                          <input type="time" name="appointment_time" id="appointment-time" class="shadow-sm focus:ring-blue-500 focus:border-blue-500 block w-full sm:text-sm border-gray-300 rounded-md" value="${formattedTime}" step="900">
                        </div>
                      </div>
                    </div>
                    <div>
                      <label for="appointment_duration" class="block text-sm font-medium text-gray-700">Duration (minutes)</label>
                      <div class="mt-1">
                        <select name="appointment_duration" id="appointment-duration" class="shadow-sm focus:ring-blue-500 focus:border-blue-500 block w-full sm:text-sm border-gray-300 rounded-md">
                          <option value="15">15 minutes</option>
                          <option value="30" selected>30 minutes</option>
                          <option value="45">45 minutes</option>
                          <option value="60">60 minutes</option>
                          <option value="90">90 minutes</option>
                        </select>
                      </div>
                    </div>
                    <div>
                      <label for="appointment_notes" class="block text-sm font-medium text-gray-700">Notes</label>
                      <div class="mt-1">
                        <textarea name="appointment_notes" id="appointment-notes" rows="3" class="shadow-sm focus:ring-blue-500 focus:border-blue-500 block w-full sm:text-sm border border-gray-300 rounded-md"></textarea>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
            <div class="bg-gray-50 px-4 py-3 sm:px-6 sm:flex sm:flex-row-reverse">
              <button type="submit" class="w-full inline-flex justify-center rounded-md border border-transparent shadow-sm px-4 py-2 bg-blue-600 text-base font-medium text-white hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 sm:ml-3 sm:w-auto sm:text-sm">
                Create Appointment
              </button>
              <button type="button" class="close-modal-btn mt-3 w-full inline-flex justify-center rounded-md border border-gray-300 shadow-sm px-4 py-2 bg-white text-base font-medium text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 sm:mt-0 sm:ml-3 sm:w-auto sm:text-sm">
                Cancel
              </button>
            </div>
            <input type="hidden" name="csrfmiddlewaretoken" value="${csrfToken}">
          </form>
        </div>
      </div>
    `;
    
    // Add to document
    document.body.appendChild(modal);
    
    // Set up patient search
    setupPatientSearch(modal.querySelector('#patient-search'), modal.querySelector('#patient-search-results'), modal.querySelector('#patient-id'));
    
    // Form submission
    const form = modal.querySelector('#create-appointment-form');
    form.addEventListener('submit', function(e) {
      e.preventDefault();
      createAppointment(new FormData(form), modal);
    });
    
    // Close modal button
    modal.querySelector('.close-modal-btn').addEventListener('click', function() {
      modal.remove();
    });
    
    // Close when clicking outside the modal
    modal.addEventListener('click', function(e) {
      if (e.target === modal) {
        modal.remove();
      }
    });
  }
  
  /**
   * Initialize patient search functionality
   */
  function initPatientSearch() {
    const patientSearch = document.getElementById('patient-search');
    const patientResults = document.getElementById('patient-search-results');
    const patientIdInput = document.getElementById('patient-id');
    
    if (patientSearch && patientResults && patientIdInput) {
      setupPatientSearch(patientSearch, patientResults, patientIdInput);
    }
  }
  
  /**
   * Set up patient search for both dashboard and modals
   */
  function setupPatientSearch(searchInput, resultsContainer, idInput) {
    if (!searchInput || !resultsContainer || !idInput) return;
    
    // Add event listeners
    searchInput.addEventListener('input', debounce(function() {
      const query = searchInput.value.trim();
      
      if (query.length < 2) {
        resultsContainer.classList.add('hidden');
        return;
      }
      
      // Get CSRF token
      const csrfToken = document.querySelector('meta[name="csrf-token"]').getAttribute('content');
      
      // Fetch patient search results
      fetch('/api/patients/search/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': csrfToken
        },
        body: JSON.stringify({ query: query })
      })
      .then(response => response.json())
      .then(data => {
        if (data.patients && data.patients.length > 0) {
          renderPatientResults(data.patients, resultsContainer, searchInput, idInput);
        } else {
          resultsContainer.innerHTML = '<div class="py-2 px-4 text-sm text-gray-500">No patients found</div>';
          resultsContainer.classList.remove('hidden');
        }
      })
      .catch(error => {
        console.error('Error searching patients:', error);
        resultsContainer.innerHTML = '<div class="py-2 px-4 text-sm text-red-500">Error searching patients</div>';
        resultsContainer.classList.remove('hidden');
      });
    }, 300));
    
    // Hide results when clicking outside
    document.addEventListener('click', function(e) {
      if (!searchInput.contains(e.target) && !resultsContainer.contains(e.target)) {
        resultsContainer.classList.add('hidden');
      }
    });
    
    // Show results when focusing on search input
    searchInput.addEventListener('focus', function() {
      if (searchInput.value.trim().length >= 2) {
        resultsContainer.classList.remove('hidden');
      }
    });
  }
  
  /**
   * Render patient search results
   */
  function renderPatientResults(patients, container, searchInput, idInput) {
    container.innerHTML = '';
    
    patients.forEach(patient => {
      const resultItem = document.createElement('div');
      resultItem.className = 'py-2 px-4 hover:bg-gray-100 cursor-pointer';
      
      const name = document.createElement('div');
      name.className = 'font-medium text-gray-900';
      name.textContent = `${patient.first_name} ${patient.last_name}`;
      
      const info = document.createElement('div');
      info.className = 'text-sm text-gray-500';
      
      // Add DOB if available
      if (patient.dob) {
        info.textContent = `DOB: ${patient.dob}`;
      } else {
        info.textContent = `Patient #${patient.id}`;
      }
      
      resultItem.appendChild(name);
      resultItem.appendChild(info);
      
      // Add click handler
      resultItem.addEventListener('click', function() {
        searchInput.value = `${patient.first_name} ${patient.last_name}`;
        idInput.value = patient.id;
        container.classList.add('hidden');
      });
      
      container.appendChild(resultItem);
    });
    
    container.classList.remove('hidden');
  }
  
  /**
   * Initialize task management system
   */
  function initTaskManagement() {
    const taskList = document.getElementById('task-list');
    if (!taskList) return;
    
    // Add drag and drop functionality if sortable.js is available
    if (typeof Sortable !== 'undefined') {
      Sortable.create(taskList, {
        animation: 150,
        ghostClass: 'bg-blue-100',
        handle: '.task-drag-handle',
        onEnd: function(evt) {
          updateTaskOrder(Array.from(taskList.children).map(item => item.dataset.taskId));
        }
      });
    }
    
    // Initialize task filter
    const taskFilter = document.getElementById('task-filter');
    if (taskFilter) {
      taskFilter.addEventListener('change', function() {
        filterTasks(this.value);
      });
    }
  }
  
  /**
   * Filter tasks by status or priority
   */
  function filterTasks(filterValue) {
    const taskItems = document.querySelectorAll('.task-item');
    
    taskItems.forEach(item => {
      if (filterValue === 'all') {
        item.classList.remove('hidden');
      } else if (filterValue.startsWith('status:')) {
        const status = filterValue.replace('status:', '');
        if (item.dataset.taskStatus === status) {
          item.classList.remove('hidden');
        } else {
          item.classList.add('hidden');
        }
      } else if (filterValue.startsWith('priority:')) {
        const priority = filterValue.replace('priority:', '');
        if (item.dataset.taskPriority === priority) {
          item.classList.remove('hidden');
        } else {
          item.classList.add('hidden');
        }
      }
    });
  }
  
  /**
   * Update task order after drag and drop
   */
  function updateTaskOrder(taskIds) {
    // Get CSRF token
    const csrfToken = document.querySelector('meta[name="csrf-token"]').getAttribute('content');
    
    // Send order update
    fetch('/api/tasks/reorder/', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': csrfToken
      },
      body: JSON.stringify({ task_ids: taskIds })
    })
    .then(response => response.json())
    .then(data => {
      if (!data.success) {
        console.error('Error updating task order:', data.message);
      }
    })
    .catch(error => {
      console.error('Error updating task order:', error);
    });
  }
  
  /**
   * Set up event listeners for doctor dashboard components
   */
  function setupEventListeners() {
    // Task completion toggle
    const taskCompletionToggles = document.querySelectorAll('.task-completion-toggle');
    taskCompletionToggles.forEach(toggle => {
      toggle.addEventListener('change', function() {
        const taskId = this.dataset.taskId;
        const isCompleted = this.checked;
        
        updateTaskCompletion(taskId, isCompleted);
      });
    });
    
    // New task form
    const newTaskForm = document.getElementById('new-task-form');
    if (newTaskForm) {
      newTaskForm.addEventListener('submit', function(e) {
        e.preventDefault();
        createNewTask(new FormData(this));
        this.reset();
      });
    }
    
    // Mark appointment as no-show
    const noShowButtons = document.querySelectorAll('.mark-no-show-btn');
    noShowButtons.forEach(button => {
      button.addEventListener('click', function() {
        const appointmentId = this.dataset.appointmentId;
        
        if (confirm('Are you sure you want to mark this appointment as no-show?')) {
          markAppointmentAsNoShow(appointmentId);
        }
      });
    });
    
    // View patient history button
    const patientHistoryButtons = document.querySelectorAll('.view-patient-history-btn');
    patientHistoryButtons.forEach(button => {
      button.addEventListener('click', function() {
        const patientId = this.dataset.patientId;
        showPatientHistory(patientId);
      });
    });
  }
  
  /**
   * Update task completion status
   */
  function updateTaskCompletion(taskId, isCompleted) {
    // Get CSRF token
    const csrfToken = document.querySelector('meta[name="csrf-token"]').getAttribute('content');
    
    // Send update request
    fetch(`/api/tasks/${taskId}/update/`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': csrfToken
      },
      body: JSON.stringify({ 
        status: isCompleted ? 'completed' : 'pending'
      })
    })
    .then(response => response.json())
    .then(data => {
      if (data.success) {
        // Update UI
        const taskItem = document.querySelector(`.task-item[data-task-id="${taskId}"]`);
        if (taskItem) {
          if (isCompleted) {
            taskItem.classList.add('bg-gray-50');
            taskItem.classList.add('opacity-75');
            taskItem.dataset.taskStatus = 'completed';
            
            // Strike through task title
            const taskTitle = taskItem.querySelector('.task-title');
            if (taskTitle) {
              taskTitle.classList.add('line-through');
            }
          } else {
            taskItem.classList.remove('bg-gray-50');
            taskItem.classList.remove('opacity-75');
            taskItem.dataset.taskStatus = 'pending';
            
            // Remove strike through
            const taskTitle = taskItem.querySelector('.task-title');
            if (taskTitle) {
              taskTitle.classList.remove('line-through');
            }
          }
        }
      } else {
        // Show error and reset toggle
        showNotification(data.message || 'Failed to update task', 'error');
        
        const toggle = document.querySelector(`.task-completion-toggle[data-task-id="${taskId}"]`);
        if (toggle) {
          toggle.checked = !isCompleted;
        }
      }
    })
    .catch(error => {
      console.error('Error updating task:', error);
      showNotification('An error occurred while updating the task', 'error');
      
      // Reset toggle
      const toggle = document.querySelector(`.task-completion-toggle[data-task-id="${taskId}"]`);
      if (toggle) {
        toggle.checked = !isCompleted;
      }
    });
  }
  
  /**
   * Create a new task
   */
  function createNewTask(formData) {
    // Get CSRF token
    const csrfToken = document.querySelector('meta[name="csrf-token"]').getAttribute('content');
    
    // Convert FormData to object
    const data = {};
    formData.forEach((value, key) => {
      data[key] = value;
    });
    
    // Send create request
    fetch('/api/tasks/create/', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': csrfToken
      },
      body: JSON.stringify(data)
    })
    .then(response => response.json())
    .then(data => {
      if (data.success && data.task) {
        // Add new task to UI
        addTaskToUI(data.task);
        showNotification('Task created successfully', 'success');
      } else {
        showNotification(data.message || 'Failed to create task', 'error');
      }
    })
    .catch(error => {
      console.error('Error creating task:', error);
      showNotification('An error occurred while creating the task', 'error');
    });
  }
  
  /**
   * Add a new task to the UI
   */
  function addTaskToUI(task) {
    const taskList = document.getElementById('task-list');
    if (!taskList) return;
    
    const taskItem = document.createElement('div');
    taskItem.className = 'task-item flex items-center p-3 border border-gray-200 rounded-lg mb-2 hover:bg-gray-50';
    taskItem.dataset.taskId = task.id;
    taskItem.dataset.taskStatus = task.status;
    taskItem.dataset.taskPriority = task.priority;
    
    // Set completed style if task is completed
    if (task.status === 'completed') {
      taskItem.classList.add('bg-gray-50', 'opacity-75');
    }
    
    // Task drag handle
    const dragHandle = document.createElement('div');
    dragHandle.className = 'task-drag-handle flex-shrink-0 cursor-move text-gray-400 mr-2';
    dragHandle.innerHTML = '<svg class="h-5 w-5" fill="currentColor" viewBox="0 0 20 20"><path d="M7 2a2 2 0 1 0 .001 4.001A2 2 0 0 0 7 2zm0 6a2 2 0 1 0 .001 4.001A2 2 0 0 0 7 8zm0 6a2 2 0 1 0 .001 4.001A2 2 0 0 0 7 14zm6-8a2 2 0 1 0-.001-4.001A2 2 0 0 0 13 6zm0 2a2 2 0 1 0 .001 4.001A2 2 0 0 0 13 8zm0 6a2 2 0 1 0 .001 4.001A2 2 0 0 0 13 14z"></path></svg>';
    
    // Checkbox
    const checkboxWrapper = document.createElement('div');
    checkboxWrapper.className = 'flex-shrink-0 mr-3';
    
    const checkbox = document.createElement('input');
    checkbox.type = 'checkbox';
    checkbox.className = 'task-completion-toggle h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded';
    checkbox.dataset.taskId = task.id;
    checkbox.checked = task.status === 'completed';
    checkbox.addEventListener('change', function() {
      updateTaskCompletion(task.id, this.checked);
    });
    
    checkboxWrapper.appendChild(checkbox);
    
    // Task content
    const content = document.createElement('div');
    content.className = 'flex-1 min-w-0';
    
    const title = document.createElement('p');
    title.className = 'task-title text-sm font-medium text-gray-900';
    if (task.status === 'completed') {
      title.classList.add('line-through');
    }
    title.textContent = task.title;
    
    const details = document.createElement('p');
    details.className = 'text-xs text-gray-500 truncate';
    
    if (task.due_date) {
      const dueDate = new Date(task.due_date);
      details.textContent = `Due: ${dueDate.toLocaleDateString()}`;
    } else {
      details.textContent = 'No due date';
    }
    
    if (task.patient_name) {
      details.textContent += ` | Patient: ${task.patient_name}`;
    }
    
    content.appendChild(title);
    content.appendChild(details);
    
    // Priority indicator
    const priorityIndicator = document.createElement('div');
    priorityIndicator.className = 'flex-shrink-0 ml-3';
    
    const indicator = document.createElement('span');
    indicator.className = 'inline-block h-2 w-2 rounded-full';
    
    if (task.priority === 'high') {
      indicator.classList.add('bg-red-500');
    } else if (task.priority === 'medium') {
      indicator.classList.add('bg-yellow-500');
    } else {
      indicator.classList.add('bg-green-500');
    }
    
    priorityIndicator.appendChild(indicator);
    
    // Assemble task item
    taskItem.appendChild(dragHandle);
    taskItem.appendChild(checkboxWrapper);
    taskItem.appendChild(content);
    taskItem.appendChild(priorityIndicator);
    
    // Add to list
    taskList.prepend(taskItem);
  }
  
  /**
   * Mark appointment as no-show
   */
  function markAppointmentAsNoShow(appointmentId) {
    // Get CSRF token
    const csrfToken = document.querySelector('meta[name="csrf-token"]').getAttribute('content');
    
    // Send update request
    fetch(`/api/appointments/${appointmentId}/no-show/`, {
      method: 'POST',
      headers: {
        'X-CSRFToken': csrfToken
      }
    })
    .then(response => response.json())
    .then(data => {
      if (data.success) {
        // Show success notification
        showNotification('Appointment marked as no-show', 'success');
        
        // Update UI
        const appointmentElement = document.querySelector(`[data-appointment-id="${appointmentId}"]`);
        if (appointmentElement) {
          const statusBadge = appointmentElement.querySelector('.status-badge');
          if (statusBadge) {
            statusBadge.className = 'status-badge px-2 py-1 text-xs font-medium rounded-full bg-red-100 text-red-800';
            statusBadge.textContent = 'No-show';
          }
          
          // Update row styles
          appointmentElement.closest('tr').classList.add('bg-red-50');
          
          // Disable action buttons
          const actionButtons = appointmentElement.querySelectorAll('button:not(.mark-no-show-btn)');
          actionButtons.forEach(button => {
            button.disabled = true;
            button.classList.add('opacity-50', 'cursor-not-allowed');
          });
          
          // Hide no-show button
          const noShowButton = appointmentElement.querySelector('.mark-no-show-btn');
          if (noShowButton) {
            noShowButton.style.display = 'none';
          }
        }
        
        // Update calendar if available
        const calendarEvent = window.doctorCalendar?.getEventById(appointmentId);
        if (calendarEvent) {
          calendarEvent.setProp('backgroundColor', '#EF4444');
          calendarEvent.setExtendedProp('status', 'no_show');
        }
      } else {
        // Show error notification
        showNotification(data.message || 'Failed to mark appointment as no-show', 'error');
      }
    })
    .catch(error => {
      console.error('Error marking appointment as no-show:', error);
      showNotification('An error occurred. Please try again.', 'error');
    });
  }
  
  /**
   * Cancel an appointment
   */
  function cancelAppointment(appointmentId, modal) {
    // Get CSRF token
    const csrfToken = document.querySelector('meta[name="csrf-token"]').getAttribute('content');
    
    // Send cancellation request
    fetch(`/api/appointments/${appointmentId}/cancel/`, {
      method: 'POST',
      headers: {
        'X-CSRFToken': csrfToken
      }
    })
    .then(response => response.json())
    .then(data => {
      if (data.success) {
        // Show success notification
        showNotification('Appointment cancelled successfully', 'success');
        
        // Close modal if provided
        if (modal) {
          modal.remove();
        }
        
        // Update UI
        const appointmentElement = document.querySelector(`[data-appointment-id="${appointmentId}"]`);
        if (appointmentElement) {
          const statusBadge = appointmentElement.querySelector('.status-badge');
          if (statusBadge) {
            statusBadge.className = 'status-badge px-2 py-1 text-xs font-medium rounded-full bg-red-100 text-red-800';
            statusBadge.textContent = 'Cancelled';
          }
          
          // Update row styles
          appointmentElement.closest('tr').classList.add('bg-red-50');
          
          // Disable action buttons
          const actionButtons = appointmentElement.querySelectorAll('button');
          actionButtons.forEach(button => {
            button.disabled = true;
            button.classList.add('opacity-50', 'cursor-not-allowed');
          });
        }
        
        // Update calendar if available
        const calendarEvent = window.doctorCalendar?.getEventById(appointmentId);
        if (calendarEvent) {
          calendarEvent.setProp('backgroundColor', '#EF4444');
          calendarEvent.setExtendedProp('status', 'cancelled');
        }
      } else {
        // Show error notification
        showNotification(data.message || 'Failed to cancel appointment', 'error');
      }
    })
    .catch(error => {
      console.error('Error cancelling appointment:', error);
      showNotification('An error occurred. Please try again.', 'error');
    });
  }
  
  /**
   * Create a new appointment
   */
  function createAppointment(formData, modal) {
    // Convert FormData to object
    const data = {};
    formData.forEach((value, key) => {
      data[key] = value;
    });
    
    // Validate form
    if (!data.patient_id) {
      showNotification('Please select a patient', 'error');
      return;
    }
    
    if (!data.appointment_date || !data.appointment_time) {
      showNotification('Please select a date and time', 'error');
      return;
    }
    
    // Send create request
    fetch('/api/appointments/create/', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded'
      },
      body: new URLSearchParams(formData)
    })
    .then(response => response.json())
    .then(data => {
      if (data.success && data.appointment) {
        // Show success notification
        showNotification('Appointment created successfully', 'success');
        
        // Close modal
        if (modal) {
          modal.remove();
        }
        
        // Add to calendar if available
        if (window.doctorCalendar) {
          window.doctorCalendar.addEvent({
            id: data.appointment.id,
            title: data.appointment.type,
            start: data.appointment.start_time,
            end: data.appointment.end_time,
            backgroundColor: '#3B82F6',
            extendedProps: {
              patient: data.appointment.patient_name,
              patientId: data.appointment.patient_id,
              status: 'confirmed',
              type: data.appointment.type,
              notes: data.appointment.notes
            }
          });
        }
        
        // Reload page if no calendar is present
        if (!window.doctorCalendar) {
          window.location.reload();
        }
      } else {
        // Show error notification
        showNotification(data.message || 'Failed to create appointment', 'error');
      }
    })
    .catch(error => {
      console.error('Error creating appointment:', error);
      showNotification('An error occurred. Please try again.', 'error');
    });
  }
  
  /**
   * Show patient history modal
   */
  function showPatientHistory(patientId) {
    // Get CSRF token
    const csrfToken = document.querySelector('meta[name="csrf-token"]').getAttribute('content');
    
    // Fetch patient history
    fetch(`/api/patients/${patientId}/history/`, {
      headers: {
        'X-CSRFToken': csrfToken
      }
    })
    .then(response => response.json())
    .then(data => {
      if (data.patient) {
        createPatientHistoryModal(data.patient, data.appointments || [], data.records || []);
      } else {
        showNotification('Failed to load patient history', 'error');
      }
    })
    .catch(error => {
      console.error('Error loading patient history:', error);
      showNotification('An error occurred. Please try again.', 'error');
    });
  }
  
  /**
   * Create patient history modal
   */
  function createPatientHistoryModal(patient, appointments, records) {
    // Create modal
    const modal = document.createElement('div');
    modal.className = 'fixed inset-0 z-50 overflow-y-auto';
    modal.innerHTML = `
      <div class="flex items-center justify-center min-h-screen px-4 pt-4 pb-20 text-center sm:block sm:p-0">
        <div class="fixed inset-0 transition-opacity" aria-hidden="true">
          <div class="absolute inset-0 bg-gray-500 opacity-75"></div>
        </div>
        <span class="hidden sm:inline-block sm:align-middle sm:h-screen" aria-hidden="true">&#8203;</span>
        <div class="inline-block align-bottom bg-white rounded-lg text-left overflow-hidden shadow-xl transform transition-all sm:my-8 sm:align-middle sm:max-w-3xl sm:w-full">
          <div class="bg-white px-4 pt-5 pb-4 sm:p-6 sm:pb-4">
            <div class="sm:flex sm:items-start">
              <div class="mt-3 text-center sm:mt-0 sm:ml-4 sm:text-left w-full">
                <div class="flex justify-between items-center mb-4">
                  <h3 class="text-lg leading-6 font-medium text-gray-900">
                    Patient History: ${patient.first_name} ${patient.last_name}
                  </h3>
                  <a href="/patients/${patient.id}/" class="text-sm text-blue-600 hover:text-blue-800">
                    View Full Profile
                  </a>
                </div>
                
                <div class="mb-6">
                  <div class="flex flex-wrap">
                    <div class="w-full md:w-1/3 mb-4 md:mb-0">
                      <p class="text-sm text-gray-500">Date of Birth</p>
                      <p class="font-medium">${patient.dob || 'Not available'}</p>
                    </div>
                    <div class="w-full md:w-1/3 mb-4 md:mb-0">
                      <p class="text-sm text-gray-500">Patient ID</p>
                      <p class="font-medium">${patient.id}</p>
                    </div>
                    <div class="w-full md:w-1/3">
                      <p class="text-sm text-gray-500">Last Visit</p>
                      <p class="font-medium">${patient.last_visit || 'No previous visits'}</p>
                    </div>
                  </div>
                </div>
                
                <div class="border-t border-gray-200 pt-4">
                  <div class="mb-4">
                    <h4 class="font-medium text-gray-800 mb-2">Recent Appointments</h4>
                    ${appointments.length > 0 ? `
                      <div class="overflow-x-auto">
                        <table class="min-w-full divide-y divide-gray-200">
                          <thead class="bg-gray-50">
                            <tr>
                              <th scope="col" class="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Date</th>
                              <th scope="col" class="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Type</th>
                              <th scope="col" class="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Status</th>
                              <th scope="col" class="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Notes</th>
                            </tr>
                          </thead>
                          <tbody class="bg-white divide-y divide-gray-200">
                            ${appointments.map(appointment => `
                              <tr>
                                <td class="px-3 py-2 whitespace-nowrap text-sm text-gray-900">${new Date(appointment.date).toLocaleDateString()}</td>
                                <td class="px-3 py-2 whitespace-nowrap text-sm text-gray-900">${appointment.type}</td>
                                <td class="px-3 py-2 whitespace-nowrap text-sm">
                                  <span class="px-2 py-1 inline-flex text-xs leading-5 font-semibold rounded-full 
                                    ${appointment.status === 'completed' ? 'bg-green-100 text-green-800' : 
                                    appointment.status === 'confirmed' ? 'bg-blue-100 text-blue-800' : 
                                    appointment.status === 'cancelled' ? 'bg-red-100 text-red-800' : 
                                    appointment.status === 'no_show' ? 'bg-red-100 text-red-800' : 
                                    'bg-yellow-100 text-yellow-800'}">
                                    ${appointment.status.charAt(0).toUpperCase() + appointment.status.slice(1)}
                                  </span>
                                </td>
                                <td class="px-3 py-2 text-sm text-gray-900">${appointment.notes || 'No notes'}</td>
                              </tr>
                            `).join('')}
                          </tbody>
                        </table>
                      </div>
                    ` : '<p class="text-sm text-gray-500">No appointment history found</p>'}
                  </div>
                  
                  <div class="mt-6">
                    <h4 class="font-medium text-gray-800 mb-2">Medical Records</h4>
                    ${records.length > 0 ? `
                      <div class="overflow-x-auto">
                        <table class="min-w-full divide-y divide-gray-200">
                          <thead class="bg-gray-50">
                            <tr>
                              <th scope="col" class="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Date</th>
                              <th scope="col" class="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Type</th>
                              <th scope="col" class="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Description</th>
                              <th scope="col" class="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Actions</th>
                            </tr>
                          </thead>
                          <tbody class="bg-white divide-y divide-gray-200">
                            ${records.map(record => `
                              <tr>
                                <td class="px-3 py-2 whitespace-nowrap text-sm text-gray-900">${new Date(record.date).toLocaleDateString()}</td>
                                <td class="px-3 py-2 whitespace-nowrap text-sm text-gray-900">${record.type}</td>
                                <td class="px-3 py-2 text-sm text-gray-900">${record.description || 'No description'}</td>
                                <td class="px-3 py-2 whitespace-nowrap text-sm">
                                  <a href="/medical/records/${record.id}/" class="text-blue-600 hover:text-blue-800">View</a>
                                </td>
                              </tr>
                            `).join('')}
                          </tbody>
                        </table>
                      </div>
                    ` : '<p class="text-sm text-gray-500">No medical records found</p>'}
                  </div>
                </div>
              </div>
            </div>
          </div>
          <div class="bg-gray-50 px-4 py-3 sm:px-6 sm:flex sm:flex-row-reverse">
            <a href="/medical/patients/${patient.id}/new-record/" class="w-full inline-flex justify-center rounded-md border border-transparent shadow-sm px-4 py-2 bg-blue-600 text-base font-medium text-white hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 sm:ml-3 sm:w-auto sm:text-sm">
              Add Medical Record
            </a>
            <a href="/appointments/schedule/?patient_id=${patient.id}" class="w-full inline-flex justify-center rounded-md border border-transparent shadow-sm px-4 py-2 bg-green-600 text-base font-medium text-white hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-green-500 sm:ml-3 sm:w-auto sm:text-sm">
              Schedule Appointment
            </a>
            <button type="button" class="close-modal-btn mt-3 w-full inline-flex justify-center rounded-md border border-gray-300 shadow-sm px-4 py-2 bg-white text-base font-medium text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 sm:mt-0 sm:ml-3 sm:w-auto sm:text-sm">
              Close
            </button>
          </div>
        </div>
      </div>
    `;
    
    // Add to document
    document.body.appendChild(modal);
    
    // Close modal button
    modal.querySelector('.close-modal-btn').addEventListener('click', function() {
      modal.remove();
    });
    
    // Close when clicking outside the modal
    modal.addEventListener('click', function(e) {
      if (e.target === modal) {
        modal.remove();
      }
    });
  }
  
  /**
   * Display a notification message
   */
  function showNotification(message, type = 'info') {
    // Check if notification container exists, create if not
    let notificationContainer = document.getElementById('notification-container');
    if (!notificationContainer) {
      notificationContainer = document.createElement('div');
      notificationContainer.id = 'notification-container';
      notificationContainer.className = 'fixed top-4 right-4 z-50 space-y-4';
      document.body.appendChild(notificationContainer);
    }
    
    // Create notification element
    const notification = document.createElement('div');
    notification.className = 'p-4 rounded-lg shadow-lg transform transition-all duration-300 translate-x-0 opacity-0 flex items-start';
    
    // Set style based on notification type
    if (type === 'success') {
      notification.classList.add('bg-green-50', 'text-green-800', 'border', 'border-green-200');
    } else if (type === 'error') {
      notification.classList.add('bg-red-50', 'text-red-800', 'border', 'border-red-200');
    } else if (type === 'warning') {
      notification.classList.add('bg-yellow-50', 'text-yellow-800', 'border', 'border-yellow-200');
    } else {
      notification.classList.add('bg-blue-50', 'text-blue-800', 'border', 'border-blue-200');
    }
    
    // Create icon based on type
    const iconWrapper = document.createElement('div');
    iconWrapper.className = 'flex-shrink-0 mr-3';
    
    let iconSvg = '';
    if (type === 'success') {
      iconSvg = '<svg class="h-5 w-5 text-green-400" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd" /></svg>';
    } else if (type === 'error') {
      iconSvg = '<svg class="h-5 w-5 text-red-400" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clip-rule="evenodd" /></svg>';
    } else if (type === 'warning') {
      iconSvg = '<svg class="h-5 w-5 text-yellow-400" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clip-rule="evenodd" /></svg>';
    } else {
      iconSvg = '<svg class="h-5 w-5 text-blue-400" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clip-rule="evenodd" /></svg>';
    }
    
    iconWrapper.innerHTML = iconSvg;
    
    // Create message content
    const contentWrapper = document.createElement('div');
    contentWrapper.className = 'flex-1';
    contentWrapper.textContent = message;
    
    // Create close button
    const closeButton = document.createElement('button');
    closeButton.className = 'ml-4 flex-shrink-0 h-5 w-5 text-gray-400 hover:text-gray-500 focus:outline-none';
    closeButton.innerHTML = '<svg class="h-5 w-5" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clip-rule="evenodd" /></svg>';
    closeButton.addEventListener('click', () => {
      removeNotification(notification);
    });
    
    // Assemble notification
    notification.appendChild(iconWrapper);
    notification.appendChild(contentWrapper);
    notification.appendChild(closeButton);
    
    // Add to container
    notificationContainer.appendChild(notification);
    
    // Animate in
    setTimeout(() => {
      notification.classList.remove('translate-x-0', 'opacity-0');
      notification.classList.add('translate-x-0', 'opacity-100');
    }, 10);
    
    // Auto-remove after delay
    setTimeout(() => {
      removeNotification(notification);
    }, 5000);
  }
  
  /**
   * Remove a notification with animation
   */
  function removeNotification(notification) {
    notification.classList.remove('translate-x-0', 'opacity-100');
    notification.classList.add('translate-x-full', 'opacity-0');
    
    setTimeout(() => {
      notification.remove();
    }, 300);
  }
  
  /**
   * Debounce function to limit how often a function can be called
   */
  function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
      const later = () => {
        clearTimeout(timeout);
        func(...args);
      };
      clearTimeout(timeout);
      timeout = setTimeout(later, wait);
    };
  }
  
  /**
   * Equalize the heights of dashboard stat cards in each row
   */
  function equalizeCardHeights() {
    // Get all stat cards in the dashboard
    const cards = document.querySelectorAll('.grid.grid-cols-1.md\\:grid-cols-4 > div');
    if (cards.length === 0) return;
    
    // Reset heights
    cards.forEach(card => {
      card.style.height = 'auto';
    });
    
    // Get the row groups (4 cards per row on large screens, 2 on medium, 1 on small)
    const viewportWidth = window.innerWidth;
    let cardsPerRow = 1;
    
    if (viewportWidth >= 768) { // md breakpoint
      cardsPerRow = 4;
    } else if (viewportWidth >= 640) { // sm breakpoint
      cardsPerRow = 2;
    }
    
    // Process each row
    for (let i = 0; i < cards.length; i += cardsPerRow) {
      const rowCards = Array.from(cards).slice(i, i + cardsPerRow);
      
      // Find tallest card in this row
      let maxHeight = 0;
      rowCards.forEach(card => {
        maxHeight = Math.max(maxHeight, card.offsetHeight);
      });
      
      // Set all cards in this row to the height of the tallest
      rowCards.forEach(card => {
        card.style.height = maxHeight + 'px';
      });
    }
    
    // Adjust main container height dynamically
    adjustDashboardHeight();
  }
  
  /**
   * Adjust the dashboard container height dynamically based on viewport and content
   */
  function adjustDashboardHeight() {
    const dashboardContainer = document.querySelector('.bg-white.shadow.rounded-lg');
    if (!dashboardContainer) return;
    
    // Reset previous styles
    dashboardContainer.style.minHeight = '';
    
    // Get the content container
    const contentSection = document.querySelector('.p-6');
    if (!contentSection) return;
    
    // Reset previous padding
    contentSection.style.minHeight = '';
    
    // Get viewport height and key elements
    const viewportHeight = window.innerHeight;
    const headerHeight = document.querySelector('.px-6.py-4.border-b.border-gray-200')?.offsetHeight || 0;
    const footerHeight = document.querySelector('footer')?.offsetHeight || 0;
    
    // Find the last grid row in the content
    const gridRows = contentSection.querySelectorAll('.grid');
    if (gridRows.length === 0) return;
    
    const lastGrid = gridRows[gridRows.length - 1];
    const lastGridBottom = lastGrid.offsetTop + lastGrid.offsetHeight;
    
    // Calculate if we need additional space
    const totalHeight = headerHeight + lastGridBottom;
    const availableHeight = viewportHeight - footerHeight - 30; // Buffer margin
    
    // Only add spacing if content is shorter than available space
    if (totalHeight < availableHeight) {
      // Add appropriate bottom margin to last grid to fill space neatly
      lastGrid.style.marginBottom = `${Math.max(0, availableHeight - totalHeight)}px`;
    } else {
      // Reset any previously set margin
      lastGrid.style.marginBottom = '';
    }
  }
});