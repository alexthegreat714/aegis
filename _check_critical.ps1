$critical = @(
    'src\core\control_loop.py',
    'src\core\policy_engine.py',
    'src\core\action_planner.py',
    'src\clients\owui_client.py',
    'src\utils\system_observer.py',
    'src\reporting\digest.py',
    'tests\test_cycle_mode.py',
    'start_aegis.bat',
    'PHASE3_IMPLEMENTATION.md',
    'SETUP_COMPLETE.md',
    'IMPLEMENTATION_STATUS.md',
    'config\policy.yaml',
    'config\settings.yaml',
    'src\aegis_logging\logger.py'
)

foreach($f in $critical) {
    if(Test-Path $f) {
        Write-Output "OK: $f"
    } else {
        Write-Output "MISSING: $f"
    }
}
