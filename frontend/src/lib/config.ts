// lib/config.ts
export const datasetConfig = {
    title: 'Public Comments on "Schedule F" Regulation',
    description: 'Comments about the proposed Schedule Policy/Career Regulation - Improving Performance, Accountability and Responsiveness in the Civil Service',
    subtitle: 'See my git repo', 
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
        title: 'Key Quote',       
        filter: 'text',
        visible: true,
        charLimit: 150
      },
      { 
        key: 'themes',       
        title: 'Themes',    
        filter: 'multi-label',
        format: 'multi-label', 
        visible: true 
      },
      { 
        key: 'rationale',
        title: 'Rationale',
        filter: 'text',
        visible: true,
        charLimit: 200
      },
      { 
        key: 'comment',   
        title: 'Comment',   
        filter: 'text', 
        visible: true,
        charLimit: 400
      },
      {
        key: 'category',
        title: 'Category',
        filter: 'select',
        visible: true,
        badges: {
          'Agency': 'bg-success',
          'Citizen': 'bg-info',
          'Union': 'bg-warning',
          'Professional Organization': 'bg-danger'
        }
      },
      {
        key: 'agencyId',
        title: 'Agency ID',
        filter: 'text',
        visible: false
      },
      { 
        key: 'link',        
        title: 'Source Link',        
        filter: 'text',
        format: 'link',
        visible: true 
      },
      { 
        key: 'id',           
        title: 'Comment ID',           
        visible: false,
        filter: 'text'
      },
      {
        key: 'hasAttachments',
        title: 'Has Attachments',
        filter: 'select',
        visible: false,
        badges: {
          'true': 'bg-success',
          'false': 'bg-danger'
        }
      },
      { 
        key: 'posted_date',
        title: 'Posted Date',
        filter: 'date',
        visible: true,
        format: 'date'
      },
      { 
        key: 'received_date',
        title: 'Received Date',
        filter: 'date',
        visible: true,
        format: 'date'
      }
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
  
  export type Field = typeof datasetConfig.fields[number];
  export type StanceType = 'For' | 'Against' | 'Neutral/Unclear';