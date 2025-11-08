$crit = @(
    'src/core/control_loop.py',
    'src/core/policy_engine.py',
    'src/core/action_planner.py',
    'src/clients/owui_client.py',
    'src/utils/system_observer.py',
    'src/reporting/digest.py',
    'tests/test_cycle_mode.py'
)

foreach($f in $crit) {
    $fwin = $f -replace '/', '\'
    $a = 'C:\Users\blyth\Desktop\Engineering\aegis\' + $fwin
    $b = 'C:\Users\blyth\aegis\' + $fwin

    if(Test-Path $a) {
        $ha = (Get-FileHash $a).Hash
    } else {
        $ha = 'MISSING'
    }

    if(Test-Path $b) {
        $hb = (Get-FileHash $b).Hash
    } else {
        $hb = 'MISSING'
    }

    Write-Output "$f;ENG=$ha;USR=$hb"
}
