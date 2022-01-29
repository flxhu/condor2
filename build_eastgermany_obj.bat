SET PYTHON="d:/Condor 2 Own Landscape/condor2/Scripts/python.exe"
SET TOOL="d:/Condor 2 Own Landscape/condor2/condor_obj_file_tool.py"

call %PYTHON% %TOOL%^
    view^
    --name EastGermany^
    --condor-obj-file EastGermany-1.2-manual-final.obj

call %PYTHON% %TOOL%^
    export^
    --name EastGermany^
    --exclude Eolienne^
    --condor-obj-file EastGermany-1.2-manual-final.obj^
    --json-file EastGermany-1.2-manual-final.json

call %PYTHON% %TOOL%^
    view^
    --name EastGermany^
    --json-file power_objects.json

call %PYTHON% %TOOL%^
    view^
    --name EastGermany^
    --json-file wind_objects.json

call %PYTHON% %TOOL%^
    import^
    --name EastGermany^
    --json-file wind_objects.json power_objects.json EastGermany-1.2-manual-final.json

PAUSE