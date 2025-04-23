// Shared JavaScript functionality for recipe management
class RecipeManager {
    // Static cache for dropdown data
    static dropdownCache = {
        workpieces: null,
        machines: null,
        tools: null,
        dataLoaded: false,
        loading: null  // Promise to track loading state
    };

    // Static method to load data once
    static async loadData() {
        if (this.dropdownCache.loading) {
            // If already loading, wait for it to complete
            return this.dropdownCache.loading;
        }

        if (this.dropdownCache.dataLoaded) {
            // If data is already loaded, return immediately
            return Promise.resolve();
        }

        // Start loading and store the promise
        this.dropdownCache.loading = (async () => {
            try {
                const [workpiecesResponse, machinesResponse, toolsResponse] = await Promise.all([
                    fetch('/engineer/recipes/workpieces'),
                    fetch('/engineer/recipes/machines'),
                    fetch('/engineer/recipes/tools')
                ]);

                this.dropdownCache.workpieces = await workpiecesResponse.json();
                this.dropdownCache.machines = await machinesResponse.json();
                this.dropdownCache.tools = await toolsResponse.json();
                this.dropdownCache.dataLoaded = true;
            } catch (error) {
                console.error('Error loading dropdown data:', error);
                showToast('Error loading form data');
                throw error;
            } finally {
                this.dropdownCache.loading = null;
            }
        })();

        return this.dropdownCache.loading;
    }

    constructor(options) {
        this.prefix = options.prefix || '';
        this.isEdit = options.isEdit || false;
        this.recipeModal = document.getElementById(options.recipeModalId);
        this.toolPositionModal = document.getElementById(options.toolPositionModalId);
        this.toolPositionsContainer = document.getElementById(this.prefix + 'ToolPositionsContainer');
        this.toolPositionGroups = document.getElementById(this.prefix + 'ToolPositionGroups');
        this.recipeForm = document.getElementById(options.recipeFormId);
        this.toolPositionForm = document.getElementById(options.toolPositionFormId);
        this.addToolPositionBtn = document.getElementById(this.prefix + 'AddToolPositionBtn');
        this.toolsData = null;
        this.toolTypes = new Set();
        this.currentEditIndex = null;
        
        window[this.getManagerName()] = this;
        this.initializeEventListeners();
        this.initialize();
    }

    async initialize() {
        await RecipeManager.loadData();
        this.setupDropdowns();
    }

    setupDropdowns() {
        // Use cached data
        this.toolsData = RecipeManager.dropdownCache.tools;

        // Extract unique tool types
        Object.values(this.toolsData).forEach(tool => {
            if (tool.type) {
                this.toolTypes.add(tool.type);
            }
        });

        const workpieceSelect = document.getElementById(this.prefix + 'Workpiece');
        const machineSelect = document.getElementById(this.prefix + 'Machine');

        if (workpieceSelect) {
            workpieceSelect.innerHTML = '<option value="">Select Workpiece</option>';
            RecipeManager.dropdownCache.workpieces.forEach(wp => {
                workpieceSelect.appendChild(new Option(wp.name, wp.id));
            });
        }

        if (machineSelect) {
            machineSelect.innerHTML = '<option value="">Select Machine</option>';
            RecipeManager.dropdownCache.machines.forEach(m => {
                machineSelect.appendChild(new Option(m.name, m.id));
            });
        }
    }

    getManagerName() {
        return this.prefix ? 'editRecipeManager' : 'createRecipeManager';
    }

    populateToolTypeSelect() {
        const toolTypeSelect = document.getElementById(this.prefix + 'ToolType');
        toolTypeSelect.innerHTML = '<option value="">Select Tool Type</option>';
        
        Array.from(this.toolTypes).sort().forEach(type => {
            toolTypeSelect.appendChild(new Option(type, type));
        });
    }

    populateToolSelect(selectedType = '') {
        if (!this.toolsData) return;
        
        const toolSelect = document.getElementById(this.prefix + 'Tool');
        toolSelect.innerHTML = '<option value="">Select Tool</option>';
        
        // Convert to array, filter by type, sort by name, then create options
        Object.entries(this.toolsData)
            .filter(([_, tool]) => !selectedType || tool.type === selectedType)
            .sort((a, b) => a[1].name.localeCompare(b[1].name))  // Sort alphabetically by name
            .forEach(([id, tool]) => {
                toolSelect.appendChild(new Option(tool.name, id));
            });
    }

    showToolPositionForm(positionName = '', toolData = null) {
        // Reset and prepare form
        this.toolPositionForm.reset();
        document.getElementById(this.prefix + 'ToolSettings').innerHTML = '';

        // Set position name if provided
        const nameInput = document.getElementById(this.prefix + 'TpName');
        if (positionName) {
            nameInput.value = positionName;
            nameInput.readOnly = true;
        } else {
            nameInput.readOnly = false;
        }

        // Populate tool type dropdown
        this.populateToolTypeSelect();

        // If editing, set tool and its data
        if (toolData) {
            const tool = this.toolsData[toolData.tool_id];
            const toolTypeSelect = document.getElementById(this.prefix + 'ToolType');
            const toolSelect = document.getElementById(this.prefix + 'Tool');
            
            if (tool && tool.type) {
                toolTypeSelect.value = tool.type;
                this.populateToolSelect(tool.type);
            } else {
                this.populateToolSelect();
            }
            
            toolSelect.value = toolData.tool_id;
            toolSelect.dispatchEvent(new Event('change'));

            document.getElementById(this.prefix + 'ExpectedLife').value = toolData.expected_life;
            document.getElementById(this.prefix + 'ToolCount').value = toolData.tool_count;
            
            // Store the tool position ID if it exists
            if (toolData.id) {
                const idInput = document.createElement('input');
                idInput.type = 'hidden';
                idInput.id = this.prefix + 'ToolPositionId';
                idInput.value = toolData.id;
                this.toolPositionForm.appendChild(idInput);
            }

            // Set tool settings after they're created by the change event
            setTimeout(() => {
                Object.entries(toolData.tool_settings).forEach(([name, value]) => {
                    const input = document.querySelector(`#${this.prefix}_${name}`);
                    if (input) input.value = value;
                });
            }, 0);
        } else {
            // Just populate the tool select with all tools initially
            this.populateToolSelect();
        }

        this.toolPositionModal.classList.add('active');
    }

    initializeEventListeners() {
        // Close buttons
        this.recipeModal.querySelector('.close').onclick = () => this.recipeModal.classList.remove('active');
        this.toolPositionModal.querySelector('.close').onclick = () => this.toolPositionModal.classList.remove('active');

        // Add tool position button (main)
        this.addToolPositionBtn.onclick = () => this.showToolPositionForm();

        // Tool type selection change
        document.getElementById(this.prefix + 'ToolType').addEventListener('change', (e) => {
            this.populateToolSelect(e.target.value);
            // Reset tool selection and settings when type changes
            document.getElementById(this.prefix + 'Tool').value = '';
            document.getElementById(this.prefix + 'ToolSettings').innerHTML = '';
        });

        // Tool selection change
        document.getElementById(this.prefix + 'Tool').addEventListener('change', (e) => {
            const toolId = e.target.value;
            const tool = this.toolsData[toolId];
            const toolSettingsDiv = document.getElementById(this.prefix + 'ToolSettings');
            toolSettingsDiv.innerHTML = '';

            if (tool && tool.settings) {
                tool.settings.forEach(attr => {
                    const attrDiv = document.createElement('div');
                    attrDiv.innerHTML = `
                        <label for="${this.prefix}_${attr.name}">${attr.name} (${attr.unit}):</label>
                        <input type="number" step="any" id="${this.prefix}_${attr.name}" name="${attr.name}" required>
                    `;
                    toolSettingsDiv.appendChild(attrDiv);
                });
            }
        });

        // Tool position form submission
        this.toolPositionForm.onsubmit = (e) => {
            e.preventDefault();
            
            const toolSelect = document.getElementById(this.prefix + 'Tool');
            const toolName = toolSelect.options[toolSelect.selectedIndex].text;
            const positionName = e.target.name.value;
            
            let group = this.toolPositionGroups.querySelector(`[data-position-name="${positionName}"]`);
            if (!group) {
                group = this.createToolPositionGroup(positionName);
            }

            const toolSettings = document.getElementById(this.prefix + 'ToolSettings').querySelectorAll('input');
            const settings = {};
            toolSettings.forEach(attr => {
                settings[attr.name] = parseFloat(attr.value);
            });

            // Get the tool position ID if it exists
            const idInput = document.getElementById(this.prefix + 'ToolPositionId');
            const toolPositionId = idInput ? idInput.value : null;

            const select = group.querySelector('.tool-select');
            
            if (this.currentEditIndex !== null) {
                // Update existing option
                const wasSelected = select.selectedIndex === this.currentEditIndex;
                const selectedTool = this.toolsData[toolSelect.value];
                const newValue = JSON.stringify({
                    id: toolPositionId,
                    tool_id: toolSelect.value,
                    tool_count: parseInt(e.target.tool_count.value),
                    expected_life: parseInt(e.target.expected_life.value),
                    tool_settings: settings,
                    tool_attributes: selectedTool.attributes
                });
                
                select.options[this.currentEditIndex].value = newValue;
                select.options[this.currentEditIndex].textContent = `${toolName} (Life: ${e.target.expected_life.value})`;
                
                if (wasSelected) {
                    select.value = newValue;
                    this.handleToolPositionChange(select);
                }
            } else {
                // Add new option
                const selectedTool = this.toolsData[toolSelect.value];
                this.addToolPositionToGroup(group, {
                    id: toolPositionId,
                    name: positionName,
                    tool_id: toolSelect.value,
                    tool_name: toolName,
                    tool_count: parseInt(e.target.tool_count.value),
                    expected_life: parseInt(e.target.expected_life.value),
                    tool_settings: settings,
                    tool_attributes: selectedTool.attributes,
                    selected: false
                });
            }

            this.toolPositionModal.classList.remove('active');
            this.toolPositionForm.reset();
            document.getElementById(this.prefix + 'ToolSettings').innerHTML = '';
            
            // Remove the ID input if it exists
            if (idInput) {
                idInput.remove();
            }
            
            // Reset edit index
            this.currentEditIndex = null;
        };

        // Recipe form submission
        this.recipeForm.onsubmit = async (e) => {
            e.preventDefault();
            const formData = new FormData(e.target);
            const recipe = {
                name: formData.get('name'),
                description: formData.get('description'),
                workpiece_id: parseInt(formData.get('workpiece_id')),
                machine_id: parseInt(formData.get('machine_id')),
            };

            if (this.isEdit) {
                recipe.id = parseInt(formData.get('recipe_id'));
            }

            try {
                const url = this.isEdit ? `/engineer/recipes/${recipe.id}` : '/engineer/recipes/';
                const toolPositions = this.collectToolPositions();
                
                const response = await fetch(url, {
                    method: this.isEdit ? 'PUT' : 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        recipe,
                        tool_positions: toolPositions
                    })
                });

                if (response.ok) {
                    showToast(`Recipe ${this.isEdit ? 'updated' : 'created'} successfully!`);
                    this.recipeModal.classList.remove('active');
                    this.recipeForm.reset();
                    this.toolPositionGroups.innerHTML = '';
                    document.body.dispatchEvent(new Event(this.isEdit ? 'Edited' : 'Added'));
                } else {
                    const result = await response.json();
                    showToast(`Error: ${result.detail || 'Unknown error'}`);
                }
            } catch (error) {
                console.error('Error:', error);
                showToast(`An error occurred`);
            }
        };
    }

    createToolPositionGroup(positionName) {
        const groupDiv = document.createElement('div');
        groupDiv.className = 'tool-position-group';
        groupDiv.dataset.positionName = positionName;
        
        const hasHighRole = window.userRole >= 4;
        
        groupDiv.innerHTML = `
            <h4>${positionName}</h4>
            <div class="tool-position-row">
                <select class="tool-select" onchange="${this.getManagerName()}.handleToolPositionChange(this)">
                    <option value="">Select Active Tool Position</option>
                </select>
                ${hasHighRole ? `
                <button type="button" class="btn-add-new" onclick="${this.getManagerName()}.addNewToolPosition('${positionName}')">
                    Add Tool Position
                </button>
                ` : ''}
            </div>
            <div class="tool-details"></div>
        `;
        
        this.toolPositionGroups.appendChild(groupDiv);
        return groupDiv;
    }

    addToolPositionToGroup(group, toolPosition) {
        const select = group.querySelector('.tool-select');
        const hasHighRole = window.userRole >= 4;
        const isInactive = toolPosition.active === false;
        if (isInactive && !hasHighRole) return;
        const option = document.createElement('option');
        option.value = JSON.stringify({
            id: toolPosition.id,
            tool_id: toolPosition.tool_id,
            tool_count: toolPosition.tool_count,
            expected_life: toolPosition.expected_life,
            tool_settings: toolPosition.tool_settings,
            tool_attributes: toolPosition.tool_attributes,
            active: toolPosition.active !== false
        });
        let label = `${toolPosition.tool_name} (Life: ${toolPosition.expected_life})`;
        if (isInactive) {
            label = `(INACTIVE) ${label}`;
            option.style.color = '#888';
        }
        option.textContent = label;
        select.appendChild(option);
        if (toolPosition.selected) {
            select.value = option.value;
            this.handleToolPositionChange(select);
        }
    }

    handleToolPositionChange(select) {
        const detailsDiv = select.closest('.tool-position-group').querySelector('.tool-details');
        if (select.value) {
            const data = JSON.parse(select.value);
            const tool = this.toolsData[data.tool_id];
            const hasHighRole = window.userRole >= 4;
            
            detailsDiv.innerHTML = `
                <div class="grid grid-cols-2 max-w-full">
                    <div>
                        <p>Expected Life: ${data.expected_life} (${data.tool_count} units)</p>
                        ${Object.entries(data.tool_settings).map(([name, value]) => {
                            const sett = tool.settings.find(a => a.name === name);
                            return `<p class="tool-setting">${name}: ${value} ${sett ? sett.unit : ''}</p>`;
                        }).join('')}
                    </div>
                    <div
                        ${data.tool_attributes.map(attr => {
                            return `<p class="tool-setting text-right">${attr.name}: ${attr.value} ${attr.unit}</p>`;
                        }).join('')}
                    </div>
                </div>
                ${hasHighRole ? `
                <div class="tool-position-actions">
                    <button type="button" class="btn-edit" onclick="${this.getManagerName()}.editToolPosition(this)">Edit</button>
                    <button type="button" class="btn-delete" onclick="${this.getManagerName()}.deleteToolPosition(this)">Delete</button>
                </div>
                ` : ''}
            `;
        } else {
            detailsDiv.innerHTML = '';
        }
    }

    addNewToolPosition(positionName) {
        this.currentEditIndex = null;
        this.showToolPositionForm(positionName);
    }

    editToolPosition(button) {
        const group = button.closest('.tool-position-group');
        const select = group.querySelector('.tool-select');
        const data = JSON.parse(select.value);
        console.log('222', data)
        
        // Store the current edit index
        this.currentEditIndex = Array.from(select.options).indexOf(select.selectedOptions[0]);
            
        this.showToolPositionForm(group.dataset.positionName, {
            id: data.id,
            tool_id: data.tool_id,
            tool_count: data.tool_count,
            expected_life: data.expected_life,
            tool_settings: data.tool_settings,
            tool_attributes: data.tool_attributes
        });
    }

    deleteToolPosition(button) {
        const group = button.closest('.tool-position-group');
        const select = group.querySelector('.tool-select');
        const selectedIndex = select.selectedIndex;
        
        select.remove(selectedIndex);
        this.handleToolPositionChange(select);
        
        if (select.options.length <= 1) {
            group.remove();
        }
    }

    collectToolPositions() {
        const positions = [];
        this.toolPositionGroups.querySelectorAll('.tool-position-group').forEach(group => {
            const positionName = group.dataset.positionName;
            const select = group.querySelector('.tool-select');
            const selectedValue = select.value;
            
            Array.from(select.options).forEach(option => {
                if (option.value) {
                    const data = JSON.parse(option.value);
                    const isSelected = option.value === selectedValue;
                    if (!data.active && !isSelected) return;
                    positions.push({
                        id: data.id,
                        name: positionName,
                        tool_id: data.tool_id,
                        tool_count: data.tool_count,
                        expected_life: data.expected_life,
                        tool_settings: data.tool_settings,
                        tool_attributes: data.tool_attributes,
                        active: isSelected ? true : data.active,
                        selected: isSelected
                    });
                }
            });
        });
        return positions;
    }

    populateEditForm(recipeData) {
        if (!this.isEdit) return;

        document.getElementById('editRecipeId').value = recipeData.id;
        document.getElementById(this.prefix + 'Name').value = recipeData.name;
        document.getElementById(this.prefix + 'Description').value = recipeData.description;
        document.getElementById(this.prefix + 'Workpiece').value = recipeData.workpiece_id;
        document.getElementById(this.prefix + 'Machine').value = recipeData.machine_id;
        
        this.toolPositionGroups.innerHTML = '';
        
        const positionGroups = {};
        recipeData.tool_positions.forEach(tp => {
            if (!positionGroups[tp.name]) {
                positionGroups[tp.name] = [];
            }
            positionGroups[tp.name].push(tp);
        });
        
        Object.entries(positionGroups).forEach(([name, positions]) => {
            const group = this.createToolPositionGroup(name);
            
                positions.forEach(tp => {
                    const tool = this.toolsData[tp.tool_id];
                    this.addToolPositionToGroup(group, {
                        id: tp.id,
                        name: tp.name,
                        tool_id: tp.tool_id,
                        tool_name: tool ? tool.name : 'Unknown Tool',
                        tool_count: tp.tool_count,
                        expected_life: tp.expected_life,
                        tool_settings: tp.tool_settings,
                        tool_attributes: tp.tool_attributes || (tool ? tool.attributes : {}),
                        active: tp.active,
                        selected: tp.selected
                    });
                });
        });
    }
}
