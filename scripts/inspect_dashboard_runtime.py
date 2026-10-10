import json
import sys
sys.stdout.reconfigure(encoding='utf-8')

with open('scratch_analysis.json') as f:
    d = json.load(f)

for k, v in d.items():
    print(f'=== Endpoint: {k} ===')
    if 'error' in v:
        print('  ERROR:', v['error'])
    elif k == '/api/dashboard':
        print('  Live:', v.get('live'))
        print('  Predictions:', v.get('predictions'))
        print('  User Controls:', v.get('user_controls'))
        rec = v.get('recommendation', {})
        print('  Recommendation Strategy:', rec.get('strategy'))
        print('  Solar Power (kW):', rec.get('solar_power'))
        print('  Battery Power (kW):', rec.get('battery_power'), 'Mode:', rec.get('battery_mode'))
        print('  Grid Power (kW):', rec.get('grid_power'))
        print('  Total Power Demand (kW):', rec.get('total_power'))
        print('  Estimated Cost (INR):', rec.get('estimated_cost'))
        print('  Q-Values:', rec.get('q_values'))
        print('  Action ID:', rec.get('action_id'))
        print('  XAI Summary:', v.get('xai', {}).get('decision_summary'))
        print('  Key Factors:', v.get('xai', {}).get('key_factors'))
    elif k == '/api/models/accuracy':
        print('  Composite Accuracy:', v.get('composite_accuracy'))
        for m, inf in v.get('models', {}).items():
            print(f'    {m}: {inf}')
    elif k == '/api/system/pipeline-verification':
        print('  Pipeline Status:', v.get('overall_status'), f"{v.get('total_latency_ms')} ms")
        for stg in v.get('stages', []):
            print(f"    Stage {stg.get('stage_num')}: {stg.get('name')} [{stg.get('status')}] - {stg.get('latency_ms')} ms")
    elif k == '/api/dataset/stats':
        print('  Dataset stats:', v.get('stats'))
        print('  Scheduler info:', v.get('scheduler'))
    elif k == '/api/battery/status':
        print('  Battery status:', v)
    elif k == '/api/energy/flow':
        print('  Energy Flow:', v)
    elif k == '/api/alerts':
        print('  Active alerts:', v)
