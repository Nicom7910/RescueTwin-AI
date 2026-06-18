from app.autonomous.mission_runner import AutonomousMissionRunner
from app.autonomous.procedural_world import ProceduralWorld
from app.autonomous.q_learning_agent import QLearningAgent
from app.autonomous.sensor_fusion import SensorFusion


def test_procedural_world_generates_dynamic_elements():
    world = ProceduralWorld(seed=123)

    assert world.width > 0
    assert world.height > 0
    assert len(world.obstacles) > 0
    assert world.remaining_victims() >= 1


def test_sensor_fusion_returns_valid_state():
    world = ProceduralWorld(seed=123)
    fusion = SensorFusion()

    reading = world.read_sensors()
    state = fusion.build_state(world.pose, reading, world.visited_ratio())

    assert state.risk_level in {"BAJO", "MEDIO", "ALTO"}
    assert 0 <= state.risk_score <= 1
    assert state.battery_level in {"ALTA", "MEDIA", "BAJA"}


def test_q_learning_agent_learns_q_value():
    world = ProceduralWorld(seed=123)
    fusion = SensorFusion()
    agent = QLearningAgent(seed=123)

    state = fusion.build_state(world.pose, world.read_sensors(), world.visited_ratio())
    action = agent.choose_action(state, training=True)
    result = world.apply_action(action)
    next_state = fusion.build_state(world.pose, world.read_sensors(), world.visited_ratio())

    agent.learn(state, action, reward=10.0, next_state=next_state)

    state_key = agent.discretize_state(state)
    assert state_key in agent.q_table
    assert agent.q_table[state_key][action] != 0.0


def test_q_learning_agent_respects_blocked_actions():
    world = ProceduralWorld(seed=123)
    fusion = SensorFusion()
    agent = QLearningAgent(seed=123, epsilon=0.0)

    state = fusion.build_state(world.pose, world.read_sensors(), world.visited_ratio())
    state_key = agent.discretize_state(state)
    agent._ensure_state(state_key)

    for action in agent.actions:
        agent.q_table[state_key][action] = 0.0

    agent.q_table[state_key]["AVANZAR"] = 100.0
    selected_action = agent.choose_action(
        state,
        training=False,
        blocked_actions={"AVANZAR"},
    )

    assert selected_action != "AVANZAR"


def test_autonomous_runner_creates_report(tmp_path):
    runner = AutonomousMissionRunner(
        output_dir=tmp_path / "reports",
        q_table_path=tmp_path / "models" / "q_table.json",
        seed=123,
    )

    report = runner.run(episodes=2, max_steps=5, training=True, verbose=False)

    assert report["episodes"] == 2
    assert report["q_table_states"] > 0
    assert (tmp_path / "reports" / "experience_log.csv").exists()
    assert (tmp_path / "reports" / "autonomous_summary.json").exists()
    assert (tmp_path / "models" / "q_table.json").exists()
