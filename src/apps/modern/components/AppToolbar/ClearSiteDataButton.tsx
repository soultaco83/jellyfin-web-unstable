import DeleteOutline from '@mui/icons-material/DeleteOutline';
import IconButton from '@mui/material/IconButton';
import Tooltip from '@mui/material/Tooltip';
import React, { useCallback } from 'react';

import globalize from 'lib/globalize';
import Dashboard from 'utils/dashboard';

const ClearSiteDataButton = () => {
    const onClick = useCallback(() => {
        void Dashboard.clearSiteData();
    }, []);

    return (
        <Tooltip title={globalize.translate('ButtonClearSiteData')}>
            <IconButton
                size='large'
                aria-label={globalize.translate('ButtonClearSiteData')}
                onClick={onClick}
                color='inherit'
            >
                <DeleteOutline />
            </IconButton>
        </Tooltip>
    );
};

export default ClearSiteDataButton;
