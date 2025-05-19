// Configuration file for the Data Explorer
window.DATASET_CONFIG = {
    title: 'Public Comments on Schedule F Regulation',
    subtitle: 'See my git repo: ', 
    datasetName: 'Comments',
    keyField: 'id',
    
    // Theme options
    theme: {
        colorScheme: 'slate',
        buttonStyle: 'flat',
        cardStyle: 'minimal'
    },
    
    fields: [

        { 
            key: 'title',         
            title: 'Title',         
            filter: 'text', 
            visible: true 
        },
        {
            key: 'stance',
            title: 'Stance',
            filter: 'select',
            visible: true,
            badges: {
                'For': 'bg-success',
                'Against': 'bg-danger',
                'Neutral/Unclear': 'bg-info'
            }
        },
        { 
            key: 'key_quote',       
            title: 'Quote',       
            filter: 'text',
            visible: true 
        },
        { 
            key: 'themes',       
            title: 'Themes',    
            filter: 'multi-label',
            format: 'multi-label', 
            visible: true 
        },
        { 
            key: 'comment',   
            title: 'Comment',   
            filter: 'text', 
            visible: false,
            charLimit: 800 
        },
        { 
            key: 'link',        
            title: 'Source Link',        
            filter: 'text',
            format: 'link',
            visible: false 
        },
        { 
            key: 'id',           
            title: 'Comment ID',           
            visible: true,
            filter: 'text'
        },
    ],
    
    stats: [
        { 
            key: 'total',        
            label: 'Total Comments',    
            type: 'count' 
        },
        { 
            key: 'stance',       
            label: 'For', 
            type: 'count', 
            match: 'For' 
        },
        { 
            key: 'stance',       
            label: 'Against', 
            type: 'count', 
            match: 'Against' 
        },
        { 
            key: 'stance',       
            label: 'Neutral/Unclear', 
            type: 'count', 
            match: 'Neutral/Unclear' 
        }
    ]
};