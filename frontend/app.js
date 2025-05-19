console.log('App.js is loading...');
console.log('Config:', window.DATASET_CONFIG);
console.log('DEBUG MODE ON - any errors will be logged to console');
(function () {
    const config = window.DATASET_CONFIG;
    const state = {
        data: [],
        table: null,
        filters: {}
    };

    document.addEventListener('DOMContentLoaded', () => {
        setupEventListeners();
        setPageTitle();
        loadData();
        
        // Add MutationObserver to handle DataTables' dynamic button creation
        setupMutationObserver();
    });

    function setupMutationObserver() {
        const observer = new MutationObserver(function(mutations) {
            mutations.forEach(function(mutation) {
                if (mutation.addedNodes.length) {
                    // Check if any buttons are added to the DOM
                    for (let i = 0; i < mutation.addedNodes.length; i++) {
                        const node = mutation.addedNodes[i];
                        if (node.classList && node.classList.contains('dt-button-collection')) {
                            // When the column visibility dropdown appears, update button states
                            setTimeout(updateColumnVisibilityButtonStates, 0);
                        }
                    }
                }
            });
        });
        
        // Start observing the document for button additions
        observer.observe(document.body, { childList: true, subtree: true });
    }

    function updateColumnVisibilityButtonStates() {
        // Clear all active classes first
        $('.dt-button-collection .dt-button').removeClass('active');
        
        // Then add active class only to visible columns
        state.table.columns().every(function(idx) {
            if (this.visible()) {
                const field = config.fields[idx];
                if (field) {
                    $('.dt-button-collection .dt-button').each(function() {
                        if ($(this).text().trim() === field.title) {
                            $(this).addClass('active');
                        }
                    });
                }
            }
        });

        // Set column visibility state for future use
        setTimeout(function() {
            const collection = $('.dt-button-collection');
            if (collection.length) {
                collection.find('button').on('click', function() {
                    // Short delay to allow DataTables to process the visibility change
                    setTimeout(function() {
                        // Update filter buttons in column headers
                        updateColumnFilterButtons();
                    }, 100);
                });
            }
        }, 50);
    }

    function setPageTitle() {
        // Set the document title using the title from config
        const title = config.title || config.datasetName || 'Data Explorer';
        document.title = title;
        document.getElementById('app-title').textContent = title;
        document.getElementById('navbar-title').textContent = title;
        
        // Set optional subtitle if present in config
        if (config.subtitle) {
            const subtitleEl = document.getElementById('navbar-subtitle');
            subtitleEl.textContent = config.subtitle;
            subtitleEl.classList.remove('d-none');
        }
    }

    function loadData() {
        // Add loading state
        document.querySelector('#statistics').classList.add('loading');
        
        fetch('data.json')
            .then(res => {
                if (!res.ok) {
                    throw new Error(`HTTP error! Status: ${res.status}`);
                }
                return res.json();
            })
            .then(data => {
                state.data = data;
                
                // Remove loading placeholders
                document.querySelector('#statistics').classList.remove('loading');
                document.querySelector('#filter-buttons').innerHTML = '';
                
                initializeTable();
                createFilterButtons();
                updateStats();
                
                // Hide "No filters" message if any filters are active
                updateNoFiltersMessage();
            })
            .catch(err => {
                document.querySelector('.card-body').innerHTML += `
                    <div class="alert alert-danger mt-3">
                        <strong>Error Loading Data:</strong><br>${err.message}
                    </div>
                `;
                
                // Remove loading indicators
                document.querySelector('#statistics').classList.remove('loading');
                document.querySelector('#filter-buttons').innerHTML = '';
            });
    }

    function initializeTable() {
        const columns = createTableColumns();

        // Destroy existing table if it exists
        if (state.table) {
            state.table.destroy();
            $('#data-table').empty();
        }

        state.table = $('#data-table').DataTable({
            data: state.data,
            columns,
            responsive: true,
            searchHighlight: true,
            fixedHeader: true,
            dom: 'ti<"dataTables_bottom d-flex align-items-center"lp>',
            pageLength: 25,
            lengthMenu: [[10, 25, 50, 100, -1], [10, 25, 50, 100, "All"]],
            language: {
                lengthMenu: "Show _MENU_ entries",
                info: "Showing _START_ to _END_ of _TOTAL_ entries",
                infoFiltered: "(filtered from _MAX_ total entries)",
                zeroRecords: "No matching records found",
                emptyTable: "No data available"
            },
            stateSave: false, // Don't save state between page reloads
            // This ensures each column has a matching name that can be used for selection
            columnDefs: config.fields.map((field, idx) => ({
                targets: idx,
                name: field.key,
                className: field.filter ? 'has-filter' : ''
            })),
            buttons: [], // Buttons are now created manually in initComplete
            // Add custom filter icons to headers after initialization
            initComplete: function() {
                // Add filter buttons to column headers
                addFilterButtonsToColumnHeaders(this.api());
                
                // Move length selector to header
                $('#dt-length-container').append($('.dataTables_length'));
                
                // Add show/hide columns button to header
                const table = this.api();
                
                // Create proper DataTables show/hide columns button
                new $.fn.dataTable.Buttons(table, {
                    buttons: [{
                        extend: 'colvis',
                        text: 'Show/Hide Columns',
                        className: 'btn btn-sm btn-primary',
                        columns: ':not(.noVis)'
                    }]
                }).container().appendTo('#dt-buttons-container');
                
                // Initialize tooltips
                setTimeout(setupTooltips, 200);
                
                // Handle various events that require tooltip re-initialization
                table.on('draw', function() {
                    setTimeout(setupTooltips, 200);
                });
                
                table.on('column-visibility.dt', function() {
                    setTimeout(setupTooltips, 200);
                });
                
                table.on('page.dt', function() {
                    setTimeout(setupTooltips, 200);
                });
            }
        });
        
        // Add event listeners for column visibility
        setupColumnVisibilityEventHandlers();
    }
    
    function createTableColumns() {
        return config.fields.map(field => ({
            data: field.key,
            title: field.title,
            visible: field.visible !== false,
            render: (data, type, row) => renderCellContent(data, type, row, field)
        }));
    }
    
    function renderCellContent(data, type, row, field) {
        // If we're requesting the raw data for sorting/filtering, return it
        if (type === 'sort' || type === 'filter') {
            return data;
        }
        
        // Handle null/undefined values
        if (data === null || data === undefined) {
            return '<span class="text-muted fst-italic">—</span>';
        }
        
        // Handle multi-label fields (skills, certifications, etc.)
        if (field.format === 'multi-label') {
            return renderMultiLabelCell(data);
        }
        
        // Handle currency formatting
        if (field.format === 'currency') {
            return `<span class="fw-medium">$${Number(data).toLocaleString()}</span>`;
        }
        
        // Handle date formatting
        if (field.format === 'date') {
            const date = new Date(data);
            if (isNaN(date)) return data;
            return date.toLocaleDateString();
        }
        
        // Handle badge formatting if badges are configured
        if (field.badges && field.badges[data]) {
            return renderBadge(data, field.badges[data]);
        }
        
        // Special case for status field for backward compatibility
        if (field.key === 'status' && !field.badges) {
            const cls = data === 'Active' ? 'bg-success' : 'bg-warning';
            return `<span class="badge ${cls}">${data}</span>`;
        }
        
        // Handle character limit with data attributes for Bootstrap tooltips
        if (field.charLimit && typeof data === 'string' && data.length > field.charLimit) {
            const truncated = data.substring(0, field.charLimit) + '...';
            
            // Escape the text for the tooltip
            const cleanData = String(data)
                .replace(/&/g, '&amp;')
                .replace(/</g, '&lt;')
                .replace(/>/g, '&gt;')
                .replace(/"/g, '&quot;')
                .replace(/'/g, '&#039;');
                
            // Use data attribute for Bootstrap tooltips
            return `<span class="char-limited" data-bs-toggle="tooltip" data-bs-placement="top" data-bs-html="false" title="${cleanData}">${truncated}</span>`;
        }
        
        // Default case - return the data as is
        return data;
    }
    
    // Helper function to escape HTML for title attributes
    function escapeHtml(text) {
        return String(text)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#039;');
    }
    
    function renderMultiLabelCell(data) {
        // Split by comma, trim whitespace, and create badges
        const items = data.split(',').map(item => item.trim()).filter(item => item);
        return items.map(item => `<span class="badge bg-secondary me-1 mb-1">${item}</span>`).join('');
    }
    
    function renderBadge(text, colorClass) {
        // Check if it's a hex color or a Bootstrap class
        if (colorClass.startsWith('#')) {
            return `<span class="badge" style="background-color: ${colorClass}">${text}</span>`;
        } else {
            return `<span class="badge ${colorClass}">${text}</span>`;
        }
    }
    
    function addFilterButtonsToColumnHeaders(api) {
        api.columns().every(function(index) {
            const column = this;
            const fieldKey = config.fields[index]?.key;
            const field = config.fields.find(f => f.key === fieldKey);
            
            // Skip if this field doesn't have a filter
            if (!field || !field.filter) return;
            
            // Get the header cell
            const headerCell = $(column.header());
            
            // Create filter button
            const filterBtn = $('<button class="column-filter-btn"><i class="bi bi-funnel"></i></button>');
            
            // Add button to header
            headerCell.css('position', 'relative');
            headerCell.append(filterBtn);
            
            // Set active class if there's a filter
            if (state.filters[field.key]) {
                filterBtn.addClass('active');
            }
            
            // Set up click handler
            filterBtn.on('click', function(e) {
                e.stopPropagation();
                showFilterModal(field);
            });
        });
    }
    
    function setupColumnVisibilityEventHandlers() {
        // Add event handler for the column visibility button
        $(document).on('click', '.buttons-colvis', function() {
            // Update button states after the dropdown is shown
            setTimeout(updateColumnVisibilityButtonStates, 50);
        });
        
        // Add listener for column visibility changes 
        state.table.on('column-visibility.dt', function(e, settings, column, visible) {
            // Re-run our filter button logic after a short delay
            setTimeout(function() {
                handleColumnVisibilityChange(settings, column, visible);
            }, 50);
        });
    }
    
    function handleColumnVisibilityChange(settings, column, visible) {
        // Get the column that changed
        const dtColumn = settings.aoColumns[column];
        const fieldKey = dtColumn.name;
        const field = config.fields.find(f => f.key === fieldKey);
        
        if (field && field.filter) {
            // Get the header cell for this column
            const headerCell = $(settings.aoColumns[column].nTh);
            
            if (visible) { // Column is now visible
                addFilterButtonToHeaderCell(headerCell, field);
                
                // Re-setup tooltips for newly visible columns
                if (field.charLimit) {
                    setTimeout(setupTooltips, 100);
                }
            } else {
                // Remove filter button when column is hidden
                headerCell.find('.column-filter-btn').remove();
            }
        }
        
        // Update the visibility dropdown if it's open
        if ($('.dt-button-collection').length) {
            updateColumnVisibilityButtonStates();
        }
    }
    
    function addFilterButtonToHeaderCell(headerCell, field) {
        // Create new filter button if needed
        if (headerCell.find('.column-filter-btn').length === 0) {
            const filterBtn = $('<button class="column-filter-btn"><i class="bi bi-funnel"></i></button>');
            headerCell.append(filterBtn);
            
            // Set active class if there's a filter
            if (state.filters[field.key]) {
                filterBtn.addClass('active');
            }
            
            // Set up click handler
            filterBtn.on('click', function(e) {
                e.stopPropagation();
                showFilterModal(field);
            });
        }
    }

    function createFilterButtons() {
        // The filter section in the sidebar is now only for showing active filters
        const container = document.getElementById('filter-buttons');
        container.innerHTML = '';
        
        // Add a note explaining how to filter
        const helpText = document.createElement('small');
        helpText.className = 'text-muted';
        helpText.innerHTML = 'Click the <i class="bi bi-funnel"></i> icon next to any column header to filter';
        container.appendChild(helpText);
    }

    function getFieldValueRange(field) {
        // Handle different field types
        let values;
        
        if (field.format === 'date') {
            // For dates, convert to timestamps
            values = state.data
                .map(row => {
                    if (!row[field.key]) return null;
                    // Try to parse the date string
                    const date = new Date(row[field.key]);
                    return isNaN(date.getTime()) ? null : date.getTime();
                })
                .filter(val => val !== null && val !== undefined);
        } else {
            // For numeric fields, use parseFloat
            values = state.data
                .map(row => parseFloat(row[field.key]))
                .filter(val => !isNaN(val) && val !== null && val !== undefined);
        }
        
        if (values.length === 0) return null;
        
        const min = Math.min(...values);
        const max = Math.max(...values);
        
        return { min, max };
    }

    // Main formatValue helper function
    function formatValue(value, field) {
        if (field.format === 'currency') {
            return '$' + value.toLocaleString();
        } else if (field.format === 'date') {
            return new Date(value).toLocaleDateString();
        } else {
            return value.toLocaleString();
        }
    }

    function showFilterModal(field) {
        const modal = document.getElementById('filter-modal');
        const existing = state.filters[field.key] || [];
        let bodyContent = '';
    
        // Create modal content based on filter type
        if (field.filter === 'select') {
            bodyContent = createSelectFilterContent(field, existing);
        } else if (field.filter === 'multi-label') {
            bodyContent = createMultiLabelFilterContent(field, existing);
        } else if (field.filter === 'numeric' || field.filter === 'currency' || field.filter === 'date') {
            bodyContent = createNumericFilterContent(field, existing);
        } else {
            bodyContent = createTextFilterContent(field, existing);
        }
    
        modal.innerHTML = `
            <div class="modal-dialog">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title">
                            <i class="bi bi-funnel me-2"></i>Filter by ${field.title}
                        </h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body">${bodyContent}</div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">
                            Cancel
                        </button>
                        <button type="button" class="btn btn-primary apply-filter">
                            Apply
                        </button>
                    </div>
                </div>
            </div>
        `;
    
        const bsModal = new bootstrap.Modal(modal);
        bsModal.show();
    
        // Focus the input field when modal shows
        setupModalEventListeners(modal, field, bsModal);
    }
    
    function createSelectFilterContent(field, existing) {
        // Get unique values and sort them
        const values = Array.from(new Set(state.data.map(row => row[field.key]))).filter(Boolean).sort();
        
        return `
            <div class="mb-3">
                <input type="text" class="form-control form-control-sm" id="select-filter-search" 
                       placeholder="Search options...">
            </div>
            <div class="select-options-container">
                ${values.map(v => `
                    <div class="form-check checkbox-item">
                        <input class="form-check-input" type="checkbox" id="check-${v.replace(/\s+/g, '-')}" 
                               value="${v}" ${existing.includes(v) ? 'checked' : ''}>
                        <label class="form-check-label" for="check-${v.replace(/\s+/g, '-')}">
                            ${v}
                        </label>
                    </div>
                `).join('')}
            </div>
            <div class="select-actions mt-3">
                <button type="button" class="btn btn-sm btn-outline-secondary select-all">Select All</button>
                <button type="button" class="btn btn-sm btn-outline-secondary ms-2 deselect-all">Deselect All</button>
            </div>
        `;
    }
    
    function createMultiLabelFilterContent(field, existing) {
        // Extract all unique labels from all rows
        const allLabels = new Set();
        state.data.forEach(row => {
            if (row[field.key]) {
                row[field.key].split(',').forEach(label => {
                    allLabels.add(label.trim());
                });
            }
        });
        const sortedLabels = Array.from(allLabels).sort();
        
        return `
            <div class="mb-3">
                <input type="text" class="form-control form-control-sm" id="multi-label-filter-search" 
                       placeholder="Search ${field.title.toLowerCase()}...">
            </div>
            <div class="multi-label-info mb-3">
                <div class="alert alert-info">
                    <small><i class="bi bi-info-circle me-2"></i>Select the ${field.title.toLowerCase()} you want to filter by. Results will show people who have <strong>any</strong> of the selected ${field.title.toLowerCase()}.</small>
                </div>
            </div>
            <div class="select-options-container">
                ${sortedLabels.map(label => `
                    <div class="form-check checkbox-item">
                        <input class="form-check-input" type="checkbox" id="check-${label.replace(/\s+/g, '-')}" 
                               value="${label}" ${existing.includes(label) ? 'checked' : ''}>
                        <label class="form-check-label" for="check-${label.replace(/\s+/g, '-')}">
                            ${label}
                        </label>
                    </div>
                `).join('')}
            </div>
            <div class="select-actions mt-3">
                <button type="button" class="btn btn-sm btn-outline-secondary select-all">Select All</button>
                <button type="button" class="btn btn-sm btn-outline-secondary ms-2 deselect-all">Deselect All</button>
            </div>
        `;
    }
    
    function createNumericFilterContent(field, existing) {
        // Get the range of values in the data
        const valueRange = getFieldValueRange(field);
        
        if (!valueRange) {
            return `
                <div class="alert alert-warning">
                    <i class="bi bi-exclamation-triangle me-2"></i>
                    No numeric data found for this field.
                </div>
            `;
        }
        
        // Check for existing numeric filters
        const existingRange = existing.range || {};
        const existingExact = existing.exact || [];
        
        // Set default range values
        const minValue = existingRange.min !== undefined ? existingRange.min : valueRange.min;
        const maxValue = existingRange.max !== undefined ? existingRange.max : valueRange.max;
        
        // Calculate step based on the range
        const step = calculateStepSize(field, valueRange);
        
        return `
            <div class="range-slider-container">
                <div class="mb-3">
                    <div class="d-flex justify-content-between align-items-center mb-2">
                        <label class="form-label fw-semibold">Range Filter</label>
                    </div>
                    
                    <div class="range-slider">
                        <div class="slider-track">
                            <div class="slider-range" id="slider-range"></div>
                        </div>
                        <input type="range" 
                               id="min-range" 
                               min="${valueRange.min}" 
                               max="${valueRange.max}" 
                               value="${minValue}" 
                               step="${step}">
                        <input type="range" 
                               id="max-range" 
                               min="${valueRange.min}" 
                               max="${valueRange.max}" 
                               value="${maxValue}" 
                               step="${step}">
                    </div>
                    
                    <div class="range-values">
                        <span id="min-value-display">${formatValue(minValue, field)}</span>
                        <span class="current-range" id="current-range">Current Range</span>
                        <span id="max-value-display">${formatValue(maxValue, field)}</span>
                    </div>
                </div>
                
                <div class="alert alert-info">
                    <small><i class="bi bi-info-circle me-2"></i>Drag the sliders to set your desired range</small>
                </div>
            </div>
            
            <div class="mb-3">
                <h6 class="fw-semibold">Exact Values</h6>
                <div class="input-group">
                    <input type="number" step="${field.format === 'currency' ? '0.01' : (field.format === 'date' ? '1' : step)}" 
                           class="form-control" id="exact-value-input" 
                           placeholder="Enter exact value and press Enter">
                    <button class="btn btn-outline-primary" type="button" id="add-exact-value">
                        Add
                    </button>
                </div>
                <div class="form-text">Add specific values to include in results</div>
            </div>
            
            <div id="exact-value-tags" class="mb-2"></div>
        `;
    }
    
    function calculateStepSize(field, valueRange) {
        let step;
        if (field.format === 'currency') {
            // For currency, use steps based on the range size
            const range = valueRange.max - valueRange.min;
            if (range > 1000000) step = 10000;
            else if (range > 100000) step = 5000;
            else if (range > 10000) step = 1000;
            else if (range > 1000) step = 100;
            else step = 10;
        } else if (field.format === 'date') {
            // For dates, use day increments
            step = 86400000; // 1 day in milliseconds
        } else {
            // For other numeric fields, calculate appropriate step
            const range = valueRange.max - valueRange.min;
            if (range > 1000) step = Math.floor(range / 100);
            else if (range > 100) step = Math.floor(range / 50);
            else step = 1;
        }
        return step;
    }
    
    function createTextFilterContent(field, existing) {
        return `
            <div class="mb-3">
                <div class="input-group">
                    <input type="text" class="form-control" id="free-text-filter" 
                           placeholder="Type and press Enter">
                    <button class="btn btn-outline-primary" type="button" id="add-text-filter">
                        Add
                    </button>
                </div>
                <div class="form-text">Press Enter or click Add after typing</div>
            </div>
            <div id="text-filter-tags" class="mb-2"></div>
        `;
    }
    
    function setupModalEventListeners(modal, field, bsModal) {
        modal.addEventListener('shown.bs.modal', function () {
            focusAppropriateInput(modal, field);
        });
    
        // Set up handlers based on filter type
        if (field.filter === 'select' || field.filter === 'multi-label') {
            setupSelectFilterHandlers(modal, field);
        }
    
        if (field.filter === 'text') {
            setupTextFilterHandlers(modal, field);
        }
    
        // Handle numeric filter setup
        if (field.filter === 'numeric' || field.filter === 'currency' || field.filter === 'date') {
            setupNumericFilterHandlers(modal, field);
        }
    
        modal.querySelector('.apply-filter').addEventListener('click', () => {
            applyFilter(modal, field, bsModal);
        });
    }
    
    function focusAppropriateInput(modal, field) {
        let inputField;
        if (field.filter === 'select') {
            inputField = document.getElementById('select-filter-search');
        } else if (field.filter === 'multi-label') {
            inputField = document.getElementById('multi-label-filter-search');
        } else if (field.filter === 'numeric' || field.filter === 'currency' || field.filter === 'date') {
            inputField = document.getElementById('min-range');
        } else {
            inputField = document.getElementById('free-text-filter');
        }
        
        if (inputField) {
            inputField.focus();
        }
    }
    
    function setupSelectFilterHandlers(modal, field) {
        const searchInputId = field.filter === 'select' ? 'select-filter-search' : 'multi-label-filter-search';
        const searchInput = modal.querySelector(`#${searchInputId}`);
        const options = modal.querySelectorAll('.checkbox-item');
        
        // Set up search functionality
        searchInput.addEventListener('input', function() {
            const searchTerm = this.value.toLowerCase();
            options.forEach(option => {
                const optionText = option.querySelector('.form-check-label').textContent.toLowerCase().trim();
                option.style.display = optionText.includes(searchTerm) ? '' : 'none';
            });
        });
        
        // Set up select/deselect all buttons
        modal.querySelector('.select-all').addEventListener('click', function() {
            const visibleCheckboxes = Array.from(options).filter(option => 
                option.style.display !== 'none'
            ).map(option => option.querySelector('input[type="checkbox"]'));
            
            visibleCheckboxes.forEach(checkbox => checkbox.checked = true);
        });
        
        modal.querySelector('.deselect-all').addEventListener('click', function() {
            const visibleCheckboxes = Array.from(options).filter(option => 
                option.style.display !== 'none'
            ).map(option => option.querySelector('input[type="checkbox"]'));
            
            visibleCheckboxes.forEach(checkbox => checkbox.checked = false);
        });
    }
    
    function setupTextFilterHandlers(modal, field) {
        const input = modal.querySelector('#free-text-filter');
        const addButton = modal.querySelector('#add-text-filter');
        const tagContainer = modal.querySelector('#text-filter-tags');
        
        // Render existing tags
        renderTextTags(field.key);

        // Add event listeners
        input.addEventListener('keydown', e => {
            if (e.key === 'Enter') {
                e.preventDefault();
                addTextFilter();
            }
        });
        
        addButton.addEventListener('click', addTextFilter);

        function addTextFilter() {
            const val = input.value.trim();
            if (val && (!state.filters[field.key] || !state.filters[field.key].includes(val))) {
                if (!state.filters[field.key]) state.filters[field.key] = [];
                state.filters[field.key].push(val);
                input.value = '';
                renderTextTags(field.key);
                input.focus();
            }
        }

        function renderTextTags(key) {
            if (!state.filters[key] || !state.filters[key].length) {
                tagContainer.innerHTML = '<div class="text-muted fst-italic">No filters added yet</div>';
                return;
            }
            
            tagContainer.innerHTML = state.filters[key].map(val => `
                <div class="filter-tag">
                    ${val}
                    <span class="remove-tag" data-val="${val}">×</span>
                </div>
            `).join('');

            tagContainer.querySelectorAll('.remove-tag').forEach(el => {
                el.addEventListener('click', () => {
                    state.filters[key] = state.filters[key].filter(v => v !== el.dataset.val);
                    renderTextTags(key);
                });
            });
        }
    }
    
    function setupNumericFilterHandlers(modal, field) {
        setupRangeSliders(modal, field);
        setupExactValueHandlers(modal, field);
    }
    
    function setupRangeSliders(modal, field) {
        const minRange = modal.querySelector('#min-range');
        const maxRange = modal.querySelector('#max-range');
        const sliderRange = modal.querySelector('#slider-range');
        const minDisplay = modal.querySelector('#min-value-display');
        const maxDisplay = modal.querySelector('#max-value-display');
        
        if (minRange && maxRange && sliderRange) {
            // Update slider visual range
            function updateSliderRange() {
                const min = parseFloat(minRange.value);
                const max = parseFloat(maxRange.value);
                const rangeMin = parseFloat(minRange.min);
                const rangeMax = parseFloat(minRange.max);
                
                // Ensure min doesn't exceed max
                if (min > max) {
                    minRange.value = max;
                }
                if (max < min) {
                    maxRange.value = min;
                }
                
                const leftPercent = ((minRange.value - rangeMin) / (rangeMax - rangeMin)) * 100;
                const rightPercent = ((maxRange.value - rangeMin) / (rangeMax - rangeMin)) * 100;
                
                sliderRange.style.left = leftPercent + '%';
                sliderRange.style.width = (rightPercent - leftPercent) + '%';
                
                minDisplay.textContent = formatValue(parseFloat(minRange.value), field);
                maxDisplay.textContent = formatValue(parseFloat(maxRange.value), field);
            }
            
            // Initial update
            updateSliderRange();
            
            // Event listeners for sliders
            minRange.addEventListener('input', updateSliderRange);
            maxRange.addEventListener('input', updateSliderRange);
        }
    }
    
    function setupExactValueHandlers(modal, field) {
        const exactInput = modal.querySelector('#exact-value-input');
        const addExactButton = modal.querySelector('#add-exact-value');
        const exactTagContainer = modal.querySelector('#exact-value-tags');
        
        if (exactInput && addExactButton && exactTagContainer) {
            // Render existing exact value tags
            renderExactValueTags(field.key);

            // Add event listeners
            exactInput.addEventListener('keydown', e => {
                if (e.key === 'Enter') {
                    e.preventDefault();
                    addExactValue();
                }
            });
            
            addExactButton.addEventListener('click', addExactValue);

            function addExactValue() {
                const val = exactInput.value.trim();
                if (val && !isNaN(val)) {
                    const numVal = parseFloat(val);
                    if (!state.filters[field.key]) state.filters[field.key] = { range: {}, exact: [] };
                    if (!state.filters[field.key].exact) state.filters[field.key].exact = [];
                    
                    if (!state.filters[field.key].exact.includes(numVal)) {
                        state.filters[field.key].exact.push(numVal);
                        exactInput.value = '';
                        renderExactValueTags(field.key);
                        exactInput.focus();
                    }
                }
            }

            function renderExactValueTags(key) {
                const exact = state.filters[key]?.exact || [];
                
                if (!exact.length) {
                    exactTagContainer.innerHTML = '<div class="text-muted fst-italic">No exact values added yet</div>';
                    return;
                }
                
                exactTagContainer.innerHTML = exact.map(val => {
                    let displayValue = val;
                    if (field.format === 'currency') {
                        displayValue = '$' + val.toLocaleString();
                    } else if (field.format === 'date') {
                        displayValue = new Date(val).toLocaleDateString();
                    }
                    
                    return `
                        <div class="filter-tag">
                            ${displayValue}
                            <span class="remove-exact-tag" data-val="${val}">×</span>
                        </div>
                    `;
                }).join('');

                exactTagContainer.querySelectorAll('.remove-exact-tag').forEach(el => {
                    el.addEventListener('click', () => {
                        const valToRemove = parseFloat(el.dataset.val);
                        state.filters[key].exact = state.filters[key].exact.filter(v => v !== valToRemove);
                        if (state.filters[key].exact.length === 0 && 
                            (!state.filters[key].range || 
                             (!state.filters[key].range.min && !state.filters[key].range.max))) {
                            delete state.filters[key];
                        }
                        renderExactValueTags(key);
                    });
                });
            }
        }
    }
    
    function applyFilter(modal, field, bsModal) {
        if (field.filter === 'select' || field.filter === 'multi-label') {
            const checked = modal.querySelectorAll('input[type=checkbox]:checked');
            state.filters[field.key] = Array.from(checked).map(cb => cb.value);
        } else if (field.filter === 'numeric' || field.filter === 'currency' || field.filter === 'date') {
            applyNumericFilter(modal, field);
        }
        bsModal.hide();
        updateTableFilters();
        renderActiveFilters();
        updateNoFiltersMessage();
    }
    
    function applyNumericFilter(modal, field) {
        const minRange = modal.querySelector('#min-range');
        const maxRange = modal.querySelector('#max-range');
        
        if (minRange && maxRange) {
            const minVal = parseFloat(minRange.value);
            const maxVal = parseFloat(maxRange.value);
            const rangeMin = parseFloat(minRange.min);
            const rangeMax = parseFloat(minRange.max);
            
            // Initialize filter object if it doesn't exist
            if (!state.filters[field.key]) {
                state.filters[field.key] = { range: {}, exact: [] };
            }
            
            // Only set range values if they're different from the full range
            if (minVal !== rangeMin || maxVal !== rangeMax) {
                state.filters[field.key].range = {
                    min: minVal,
                    max: maxVal
                };
            } else {
                state.filters[field.key].range = {};
            }
            
            // Clean up empty filters
            if ((!state.filters[field.key].range || 
                 (!state.filters[field.key].range.min && !state.filters[field.key].range.max)) &&
                (!state.filters[field.key].exact || state.filters[field.key].exact.length === 0)) {
                delete state.filters[field.key];
            }
        }
    }

    function renderExactValueTags(key) {
        const field = config.fields.find(f => f.key === key);
        const exact = state.filters[key]?.exact || [];
        const exactTagContainer = document.getElementById('exact-value-tags');
        
        if (!exactTagContainer) return;
        
        if (!exact.length) {
            exactTagContainer.innerHTML = '<div class="text-muted fst-italic">No exact values added yet</div>';
            return;
        }
        
        exactTagContainer.innerHTML = exact.map(val => {
            let displayValue = val;
            if (field.format === 'currency') {
                displayValue = '$' + val.toLocaleString();
            } else if (field.format === 'date') {
                displayValue = new Date(val).toLocaleDateString();
            }
            
            return `
                <div class="filter-tag">
                    ${displayValue}
                    <span class="remove-exact-tag" data-val="${val}">×</span>
                </div>
            `;
        }).join('');

        exactTagContainer.querySelectorAll('.remove-exact-tag').forEach(el => {
            el.addEventListener('click', () => {
                const valToRemove = parseFloat(el.dataset.val);
                state.filters[key].exact = state.filters[key].exact.filter(v => v !== valToRemove);
                if (state.filters[key].exact.length === 0 && 
                    (!state.filters[key].range || 
                     (!state.filters[key].range.min && !state.filters[key].range.max))) {
                    delete state.filters[key];
                }
                renderExactValueTags(key);
            });
        });
    }

    function renderTextTags(key) {
        const tagContainer = document.getElementById('text-filter-tags');
        
        if (!tagContainer) return;
        
        if (!state.filters[key] || !state.filters[key].length) {
            tagContainer.innerHTML = '<div class="text-muted fst-italic">No filters added yet</div>';
            return;
        }
        
        tagContainer.innerHTML = state.filters[key].map(val => `
            <div class="filter-tag">
                ${val}
                <span class="remove-tag" data-val="${val}">×</span>
            </div>
        `).join('');

        tagContainer.querySelectorAll('.remove-tag').forEach(el => {
            el.addEventListener('click', () => {
                state.filters[key] = state.filters[key].filter(v => v !== el.dataset.val);
                renderTextTags(key);
            });
        });
    }

    function updateTableFilters(redraw = true) {
        $.fn.dataTable.ext.search = [];

        $.fn.dataTable.ext.search.push((settings, data, dataIndex) => {
            const row = state.data[dataIndex];
            for (let key in state.filters) {
                if (!state.filters[key]) continue;
                
                const field = config.fields.find(f => f.key === key);
                const filterValue = state.filters[key];
                
                if (field && (field.filter === 'numeric' || field.filter === 'currency' || field.filter === 'date')) {
                    if (!applyNumericFieldFilter(row, field, filterValue)) {
                        return false;
                    }
                } else if (Array.isArray(filterValue)) {
                    if (!applyArrayFieldFilter(row, field, filterValue)) {
                        return false;
                    }
                }
            }
            return true;
        });

        if (redraw) {
            state.table.draw();
            updateStats();
        }
    }
    
    function applyNumericFieldFilter(row, field, filterValue) {
        // Handle numeric/currency/date filters
        if (filterValue.range || filterValue.exact) {
            let cellValue;
            
            // Handle date fields properly
            if (field.format === 'date') {
                const date = new Date(row[field.key]);
                cellValue = isNaN(date.getTime()) ? NaN : date.getTime();
            } else {
                cellValue = parseFloat(row[field.key]);
            }
            
            if (isNaN(cellValue)) {
                return false;
            }
            
            // Check range constraints
            if (filterValue.range && (filterValue.range.min !== undefined || filterValue.range.max !== undefined)) {
                // Get the actual data range for comparison
                const valueRange = getFieldValueRange(field);
                const isFullRange = valueRange && 
                    (filterValue.range.min === undefined || filterValue.range.min === valueRange.min) && 
                    (filterValue.range.max === undefined || filterValue.range.max === valueRange.max);
                
                // If it's not the full range, apply the filter
                if (!isFullRange) {
                    if (filterValue.range.min !== undefined && cellValue < filterValue.range.min) {
                        return false;
                    }
                    if (filterValue.range.max !== undefined && cellValue > filterValue.range.max) {
                        return false;
                    }
                }
            }
            
            // Check exact values
            if (filterValue.exact && filterValue.exact.length > 0) {
                // If we have exact values, the value must either match an exact value OR be within range
                const matchesExact = filterValue.exact.includes(cellValue);
                const matchesRange = (!filterValue.range || 
                    ((!filterValue.range.min || cellValue >= filterValue.range.min) &&
                     (!filterValue.range.max || cellValue <= filterValue.range.max)));
                
                if (!matchesExact && !matchesRange) {
                    return false;
                }
            }
        }
        return true;
    }
    
    function applyArrayFieldFilter(row, field, filterValue) {
        // Handle array-based filters (select, multi-label, text)
        if (filterValue.length === 0) return true;
        
        if (field && field.filter === 'multi-label') {
            // For multi-label fields, check if any selected filter values are present
            const cellVal = String(row[field.key] || '');
            const cellLabels = cellVal.split(',').map(label => label.trim());
            
            // Check if any of the selected filters match any of the cell's labels
            const hasMatch = filterValue.some(filterVal => 
                cellLabels.some(cellLabel => cellLabel.toLowerCase().includes(filterVal.toLowerCase()))
            );
            
            if (!hasMatch) {
                return false;
            }
        } else {
            // Standard filtering for other types
            const cellVal = String(row[field.key] || '').toLowerCase();
            if (!filterValue.some(f => cellVal.includes(f.toLowerCase()))) {
                return false;
            }
        }
        return true;
    }

    // Extract updateColumnFilterButtons as a standalone function
    function updateColumnFilterButtons() {
        if (state.table) {
            state.table.columns().every(function(index) {
                const column = this;
                const headerCell = $(column.header());
                const filterBtn = headerCell.find('.column-filter-btn');
                const fieldKey = config.fields[index]?.key;
                
                if (fieldKey && filterBtn.length) {
                    if (state.filters[fieldKey]) {
                        filterBtn.addClass('active');
                    } else {
                        filterBtn.removeClass('active');
                    }
                }
            });
        }
    }

    function renderActiveFilters() {
        const container = document.getElementById('active-filters');
        container.innerHTML = '';
        
        // Update filter buttons in column headers to show which are active
        updateColumnFilterButtons();
    
        let hasFilters = false;
        
        Object.entries(state.filters).forEach(([key, filterValue]) => {
            if (!filterValue) return;
            
            hasFilters = true;
            const field = config.fields.find(f => f.key === key);
            const title = field?.title || key;
            
            if (Array.isArray(filterValue)) {
                renderArrayFilterTags(container, key, filterValue, title);
            } else if (filterValue.range || filterValue.exact) {
                renderNumericFilterTags(container, key, filterValue, field, title);
            }
        });
        
        return hasFilters;
    }
    
    function renderArrayFilterTags(container, key, filterValue, title) {
        // Handle array-based filters
        if (filterValue.length === 0) return;
        
        filterValue.forEach(val => {
            const tag = document.createElement('div');
            tag.className = 'filter-tag';
            tag.innerHTML = `
                ${title}: ${val}
                <span class="remove-tag" data-key="${key}" data-val="${val}">×</span>
            `;
            tag.querySelector('.remove-tag').addEventListener('click', () => {
                state.filters[key] = state.filters[key].filter(v => v !== val);
                if (state.filters[key].length === 0) delete state.filters[key];
                updateTableFilters();
                renderActiveFilters();
                updateNoFiltersMessage();
            });
            container.appendChild(tag);
        });
    }
    
    function renderNumericFilterTags(container, key, filterValue, field, title) {
        // Handle numeric filters
        if (filterValue.range && (filterValue.range.min !== undefined || filterValue.range.max !== undefined)) {
            renderRangeFilterTag(container, key, filterValue, field, title);
        }
        
        // Handle exact values
        if (filterValue.exact && filterValue.exact.length > 0) {
            renderExactValueFilterTags(container, key, filterValue.exact, field, title);
        }
    }
    
    function renderRangeFilterTag(container, key, filterValue, field, title) {
        const tag = document.createElement('div');
        tag.className = 'filter-tag';
        
        // Get the full range for comparison
        const valueRange = getFieldValueRange(field);
        const isFullRange = valueRange && 
            filterValue.range.min === valueRange.min && 
            filterValue.range.max === valueRange.max;
        
        // Only show range tag if it's not the full range
        if (!isFullRange) {
            let rangeText = '';
            let minDisplay = filterValue.range.min !== undefined ? formatValue(filterValue.range.min, field) : formatValue(valueRange?.min || 0, field);
            let maxDisplay = filterValue.range.max !== undefined ? formatValue(filterValue.range.max, field) : formatValue(valueRange?.max || 0, field);
            
            rangeText = `${minDisplay} - ${maxDisplay}`;
            
            tag.innerHTML = `
                ${title}: ${rangeText}
                <span class="remove-range-tag" data-key="${key}">×</span>
            `;
            tag.querySelector('.remove-range-tag').addEventListener('click', () => {
                if (filterValue.exact && filterValue.exact.length > 0) {
                    // Keep exact values, just remove range
                    filterValue.range = {};
                } else {
                    // Remove entire filter
                    delete state.filters[key];
                }
                updateTableFilters();
                renderActiveFilters();
                updateNoFiltersMessage();
            });
            container.appendChild(tag);
        }
    }
    
    function renderExactValueFilterTags(container, key, exactValues, field, title) {
        exactValues.forEach(val => {
            const tag = document.createElement('div');
            tag.className = 'filter-tag';
            let displayVal = formatValue(val, field);
            
            tag.innerHTML = `
                ${title}: ${displayVal}
                <span class="remove-exact-tag" data-key="${key}" data-val="${val}">×</span>
            `;
            tag.querySelector('.remove-exact-tag').addEventListener('click', () => {
                state.filters[key].exact = state.filters[key].exact.filter(v => v !== val);
                if (state.filters[key].exact.length === 0 && 
                    (!state.filters[key].range || 
                     (!state.filters[key].range.min && !state.filters[key].range.max))) {
                    delete state.filters[key];
                }
                updateTableFilters();
                renderActiveFilters();
                updateNoFiltersMessage();
            });
            container.appendChild(tag);
        });
    }

    function updateNoFiltersMessage() {
        const noFiltersMsg = document.getElementById('no-filters-message');
        const hasActiveFilters = hasAnyActiveFilters();
        
        if (noFiltersMsg) {
            noFiltersMsg.style.display = hasActiveFilters ? 'none' : 'block';
        }
        
        // Update the filter container class
        const activeFiltersContainer = document.querySelector('.active-filters-container');
        if (activeFiltersContainer) {
            if (hasActiveFilters) {
                activeFiltersContainer.classList.add('has-filters');
            } else {
                activeFiltersContainer.classList.remove('has-filters');
            }
        }
        
        // Update the card header to indicate active filters
        updateFilterHeader(hasActiveFilters);
    }
    
    function hasAnyActiveFilters() {
        return Object.values(state.filters).some(filterValue => {
            if (Array.isArray(filterValue)) {
                return filterValue.length > 0;
            } else if (filterValue && typeof filterValue === 'object') {
                return (filterValue.range && (filterValue.range.min !== undefined || filterValue.range.max !== undefined)) ||
                       (filterValue.exact && filterValue.exact.length > 0);
            }
            return false;
        });
    }
    
    function updateFilterHeader(hasActiveFilters) {
        const filterHeader = document.querySelector('.card-header h5 i.bi-funnel');
        if (filterHeader) {
            const parentElement = filterHeader.parentElement;
            if (hasActiveFilters) {
                parentElement.innerHTML = '<i class="bi bi-funnel-fill me-2"></i>Active Filters';
            } else {
                parentElement.innerHTML = '<i class="bi bi-funnel me-2"></i>Filters';
            }
        }
    }

    function clearFilters() {
        state.filters = {};
        renderActiveFilters();
        updateTableFilters();
        updateNoFiltersMessage();
    }

    function updateStats() {
        const stats = config.stats;
        const visibleData = getVisibleData();

        const container = document.getElementById('statistics');
        container.innerHTML = '<div class="row text-center"></div>';
        const row = container.querySelector('.row');

        stats.forEach(stat => {
            let value = calculateStatValue(stat, visibleData);
            let formattedValue = formatStatValue(value, stat);

            const statHTML = `
                <div class="col">
                    <h3>${formattedValue}</h3>
                    <p>${stat.label}</p>
                </div>
            `;
            row.innerHTML += statHTML;
        });
    }
    
    function calculateStatValue(stat, visibleData) {
        let value = null;
        
        switch (stat.type) {
            case 'count':
                if (stat.key === 'total') {
                    value = visibleData.length;
                } else if (stat.match !== undefined) {
                    value = visibleData.filter(row => String(row[stat.key]) === stat.match).length;
                } else {
                    value = visibleData.filter(row => row[stat.key] !== undefined).length;
                }
                break;

            case 'unique':
                const uniqueValues = new Set(visibleData.map(row => row[stat.key]).filter(Boolean));
                value = uniqueValues.size;
                break;

            case 'mean':
                const validValues = visibleData
                    .map(row => parseFloat(row[stat.key]))
                    .filter(val => !isNaN(val));
                
                if (validValues.length > 0) {
                    const sum = validValues.reduce((a, b) => a + b, 0);
                    value = sum / validValues.length;
                } else {
                    value = 0;
                }
                break;

            case 'min':
                const minValues = visibleData
                    .map(row => parseFloat(row[stat.key]))
                    .filter(val => !isNaN(val));
                
                if (minValues.length > 0) {
                    value = Math.min(...minValues);
                } else {
                    value = 0;
                }
                break;
                
            case 'max':
                const maxValues = visibleData
                    .map(row => parseFloat(row[stat.key]))
                    .filter(val => !isNaN(val));
                
                if (maxValues.length > 0) {
                    value = Math.max(...maxValues);
                } else {
                    value = 0;
                }
                break;

            case 'sum':
                const sumValues = visibleData
                    .map(row => parseFloat(row[stat.key]))
                    .filter(val => !isNaN(val));
                
                if (sumValues.length > 0) {
                    value = sumValues.reduce((a, b) => a + b, 0);
                } else {
                    value = 0;
                }
                break;
        }
        
        return value;
    }
    
    function formatStatValue(value, stat) {
        let formattedValue = '';
        
        if (stat.type === 'count' || stat.type === 'unique') {
            formattedValue = value.toLocaleString();
        } else if (stat.type === 'mean') {
            if (stat.format === 'currency') {
                formattedValue = `$${value.toLocaleString(undefined, { minimumFractionDigits: 0, maximumFractionDigits: 0 })}`;
            } else {
                formattedValue = value.toLocaleString(undefined, { minimumFractionDigits: 0, maximumFractionDigits: 2 });
            }
        } else if (stat.type === 'min' || stat.type === 'max' || stat.type === 'sum') {
            if (stat.format === 'currency') {
                formattedValue = `$${value.toLocaleString()}`;
            } else {
                formattedValue = value.toLocaleString();
            }
        }
        
        return formattedValue;
    }

    // Helper function to get data that's currently visible after filtering
    function getVisibleData() {
        // If no filters are applied, return all data
        if (!hasAnyActiveFilters()) {
            return state.data;
        }

        // Otherwise, apply filters manually
        return state.data.filter(row => {
            for (let key in state.filters) {
                const filterValue = state.filters[key];
                
                // Skip empty filter arrays or objects
                if (!filterValue) continue;
                
                const field = config.fields.find(f => f.key === key);
                
                if (field && (field.filter === 'numeric' || field.filter === 'currency' || field.filter === 'date')) {
                    if (!applyNumericFieldFilter(row, field, filterValue)) {
                        return false;
                    }
                } else if (Array.isArray(filterValue)) {
                    if (!applyArrayFieldFilter(row, field, filterValue)) {
                        return false;
                    }
                }
            }
            return true;
        });
    }

    function exportCSV() {
        const visibleData = getVisibleData();
        
        if (visibleData.length === 0) {
            alert('No data to export');
            return;
        }
        
        // Get visible columns
        const visibleFields = config.fields.filter(f => {
            const columnIdx = state.table.column(f.key + ':name').index();
            return columnIdx === undefined || state.table.column(columnIdx).visible();
        });
        
        const headers = visibleFields.map(f => f.title);
        let csv = headers.join(',') + '\n';

        visibleData.forEach(row => {
            const line = visibleFields.map(f => {
                let val = row[f.key] ?? '';
                
                // Format value if needed
                if (f.format === 'currency' && val !== '') {
                    val = Number(val).toLocaleString().replace(/,/g, '');
                }
                
                // Format date if needed
                if (f.format === 'date' && val !== '') {
                    val = new Date(val).toLocaleDateString();
                }
                
                // Handle commas and quotes
                val = String(val).replace(/"/g, '""');
                return val.includes(',') || val.includes('"') ? `"${val}"` : val;
            });
            csv += line.join(',') + '\n';
        });

        downloadCSV(csv);
    }
    
    function downloadCSV(csvContent) {
        const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        
        const timestamp = new Date().toISOString().replace(/[:.]/g, '-').substring(0, 19);
        const filename = `${config.title || 'export'}-${timestamp}.csv`;
        
        a.href = url;
        a.download = filename;
        a.hidden = true;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    }
    
    // Function to set up click-to-expand for character-limited cells
    // Initialize Bootstrap tooltips
    function setupTooltips() {
        try {
            // Find all tooltip elements
            const tooltipTriggerList = document.querySelectorAll('[data-bs-toggle="tooltip"]');
            console.log('Found tooltip elements:', tooltipTriggerList.length);
            
            // Initialize each tooltip
            [...tooltipTriggerList].forEach(tooltipTriggerEl => {
                try {
                    // Dispose existing tooltip if any
                    const existingTooltip = bootstrap.Tooltip.getInstance(tooltipTriggerEl);
                    if (existingTooltip) {
                        existingTooltip.dispose();
                    }
                    
                    // Create new tooltip
                    new bootstrap.Tooltip(tooltipTriggerEl, {
                        boundary: document.body,
                        trigger: 'hover focus',
                        container: 'body'
                    });
                } catch (err) {
                    console.error('Error initializing tooltip:', err);
                }
            });
        } catch (err) {
            console.error('Error in setupTooltips:', err);
        }
    }

    function setupEventListeners() {
        document.getElementById('export-csv').addEventListener('click', exportCSV);
        document.getElementById('clear-filters').addEventListener('click', clearFilters);
    }
})();