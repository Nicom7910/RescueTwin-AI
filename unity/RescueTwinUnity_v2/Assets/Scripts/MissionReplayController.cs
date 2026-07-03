using System;
using System.Collections.Generic;
using System.IO;
using UnityEngine;

[Serializable]
public class MissionStep
{
    public int step;
    public int x;
    public int y;
    public string action;
    public string risk_level;
    public string battery_level;
    public string[] blocked_actions;
    public bool escape_mode;
    public bool return_to_base_mode;

    public bool victim_detected;
    public bool victim_search_mode;
    public bool victim_found;
    public int victim_x;
    public int victim_y;
    public int victim_target_x;
    public int victim_target_y;
    public string message;
}

[Serializable]
public class MissionStepList
{
    public List<MissionStep> steps;
}

public class MissionReplayController : MonoBehaviour
{
    [Header("Mission file")]
    public string missionFileName = "demo_001_trajectory.json";

    [Header("Scene references")]
    public Transform robot;
    public Transform baseMarker;
    public MissionMapBuilder mapBuilder;

    [Header("Replay settings")]
    public float cellSize = 1.0f;
    public float stepDuration = 0.32f;
    public float robotHeight = 0.38f;
    public bool loopReplay = true;
    public float rotationSmoothness = 10f;

    [Header("Map settings")]
    public int mapWidth = 20;
    public int mapHeight = 20;

    [Header("Demo selector")]
    public bool useDemoSelector = true;
    public int currentDemo = 1;

    [Tooltip("Se actualiza automáticamente según los archivos demo_XXX encontrados en StreamingAssets.")]
    public int maxDemo = 1;

    [Header("Visual trail")]
    public LineRenderer trailLine;

    [Header("Victim found marker")]
    public GameObject victimFoundMarkerPrefab;

    private List<MissionStep> steps = new List<MissionStep>();
    private int currentIndex = 0;
    private float timer = 0f;

    private Vector3 startPosition;
    private Vector3 targetPosition;

    private Quaternion startRotation;
    private Quaternion targetRotation;

    private MissionStep currentStep;

    private GUIStyle hudStyle;
    private GUIStyle titleStyle;
    private GUIStyle modeStyle;
    private GUIStyle helpStyle;
    private GUIStyle victimStyle;

    private bool victimAlreadyMarked = false;
    private Vector2Int lastVictimLocation = new Vector2Int(-1, -1);
    private GameObject victimFoundMarker;

    void Start()
    {
        SetupTrail();
        SetupHudStyles();

        if (useDemoSelector)
        {
            DetectAvailableDemos();
            currentDemo = Mathf.Clamp(currentDemo, 1, maxDemo);
            LoadDemo(currentDemo);
        }
        else
        {
            LoadManualMission();
        }
    }

    void Update()
    {
        HandleKeyboardInput();

        if (robot == null || steps.Count == 0)
        {
            return;
        }

        timer += Time.deltaTime;
        float t = Mathf.Clamp01(timer / stepDuration);

        robot.position = Vector3.Lerp(startPosition, targetPosition, t);
        robot.rotation = Quaternion.Slerp(startRotation, targetRotation, t);

        if (t >= 1f)
        {
            AdvanceStep();
        }
    }

    private void DetectAvailableDemos()
    {
        int detected = 0;

        for (int i = 1; i <= 9; i++)
        {
            string demoId = i.ToString("D3");

            string trajectoryPath = Path.Combine(
                Application.streamingAssetsPath,
                "demo_" + demoId + "_trajectory.json"
            );

            string worldPath = Path.Combine(
                Application.streamingAssetsPath,
                "demo_" + demoId + "_world.json"
            );

            bool hasTrajectory = File.Exists(trajectoryPath);
            bool hasWorld = File.Exists(worldPath);

            if (hasTrajectory && hasWorld)
            {
                detected = i;
            }
            else
            {
                Debug.Log(
                    "[MissionReplayController] Demo " + demoId +
                    " incompleta o ausente. trajectory=" + hasTrajectory +
                    " world=" + hasWorld
                );
            }
        }

        if (detected > 0)
        {
            maxDemo = detected;
            Debug.Log("[MissionReplayController] Demos detectadas automáticamente: " + maxDemo);
        }
        else
        {
            maxDemo = 1;
            Debug.LogWarning("[MissionReplayController] No se detectaron demos. Se usará maxDemo = 1.");
        }
    }

    private void HandleKeyboardInput()
    {
        if (useDemoSelector)
        {
            if (maxDemo >= 1 && Input.GetKeyDown(KeyCode.Alpha1)) LoadDemo(1);
            if (maxDemo >= 2 && Input.GetKeyDown(KeyCode.Alpha2)) LoadDemo(2);
            if (maxDemo >= 3 && Input.GetKeyDown(KeyCode.Alpha3)) LoadDemo(3);
            if (maxDemo >= 4 && Input.GetKeyDown(KeyCode.Alpha4)) LoadDemo(4);
            if (maxDemo >= 5 && Input.GetKeyDown(KeyCode.Alpha5)) LoadDemo(5);
            if (maxDemo >= 6 && Input.GetKeyDown(KeyCode.Alpha6)) LoadDemo(6);
            if (maxDemo >= 7 && Input.GetKeyDown(KeyCode.Alpha7)) LoadDemo(7);
            if (maxDemo >= 8 && Input.GetKeyDown(KeyCode.Alpha8)) LoadDemo(8);
            if (maxDemo >= 9 && Input.GetKeyDown(KeyCode.Alpha9)) LoadDemo(9);
        }

        if (Input.GetKeyDown(KeyCode.R))
        {
            RestartCurrentDemo();
        }
    }

    public void LoadDemo(int demoNumber)
    {
        DetectAvailableDemos();

        demoNumber = Mathf.Clamp(demoNumber, 1, maxDemo);
        currentDemo = demoNumber;

        string demoId = demoNumber.ToString("D3");

        missionFileName = "demo_" + demoId + "_trajectory.json";
        string worldFileName = "demo_" + demoId + "_world.json";

        string trajectoryPath = Path.Combine(Application.streamingAssetsPath, missionFileName);
        string worldPath = Path.Combine(Application.streamingAssetsPath, worldFileName);

        if (!File.Exists(trajectoryPath))
        {
            Debug.LogError("[MissionReplayController] No existe trajectory: " + trajectoryPath);
            return;
        }

        if (!File.Exists(worldPath))
        {
            Debug.LogError("[MissionReplayController] No existe world: " + worldPath);
            return;
        }

        if (mapBuilder != null)
        {
            mapBuilder.LoadAndBuildWorld(worldFileName, missionFileName);
            mapWidth = mapBuilder.mapWidth;
            mapHeight = mapBuilder.mapHeight;
            cellSize = mapBuilder.cellSize;
        }
        else
        {
            Debug.LogWarning("[MissionReplayController] mapBuilder no asignado. Solo se cargará trayectoria.");
        }

        LoadMission();
        RestartCurrentDemo();

        Debug.Log(
            "[MissionReplayController] Demo cargada: " + currentDemo +
            " / " + maxDemo +
            " | trajectory=" + missionFileName +
            " | world=" + worldFileName
        );
    }

    public void LoadManualMission()
    {
        if (mapBuilder != null)
        {
            mapBuilder.LoadAndBuildWorld(
                mapBuilder.worldFileName,
                missionFileName
            );

            mapWidth = mapBuilder.mapWidth;
            mapHeight = mapBuilder.mapHeight;
            cellSize = mapBuilder.cellSize;
        }

        LoadMission();
        RestartCurrentDemo();

        Debug.Log("[MissionReplayController] Misión manual cargada: " + missionFileName);
    }

    private void RestartCurrentDemo()
    {
        if (steps.Count == 0 || robot == null)
        {
            Debug.LogWarning("[MissionReplayController] No se puede reiniciar: sin pasos o sin robot.");
            return;
        }

        ClearTrail();
        ClearVictimFoundMarker();

        victimAlreadyMarked = false;
        lastVictimLocation = new Vector2Int(-1, -1);

        currentIndex = 0;
        currentStep = steps[currentIndex];

        Vector3 initialPosition = GridToWorld(currentStep.x, currentStep.y);
        robot.position = initialPosition;

        Quaternion initialRotation = Quaternion.identity;

        if (steps.Count > 1)
        {
            Vector3 nextPosition = GridToWorld(steps[1].x, steps[1].y);
            initialRotation = CalculateTargetRotation(
                initialPosition,
                nextPosition,
                Quaternion.identity
            );
        }

        robot.rotation = initialRotation;

        startPosition = initialPosition;
        targetPosition = initialPosition;

        startRotation = initialRotation;
        targetRotation = initialRotation;

        timer = 0f;

        SetupBaseMarker();
        ApplyRobotVisualState(currentStep);
        AddTrailPoint(initialPosition);
        CheckVictimFound(currentStep);
    }

    private void LoadMission()
    {
        string path = Path.Combine(Application.streamingAssetsPath, missionFileName);

        if (!File.Exists(path))
        {
            Debug.LogError("[MissionReplayController] No se encontró el archivo de misión: " + path);
            steps = new List<MissionStep>();
            currentStep = null;
            return;
        }

        string json = File.ReadAllText(path);
        string wrappedJson = "{\"steps\":" + json + "}";

        MissionStepList loaded = JsonUtility.FromJson<MissionStepList>(wrappedJson);

        if (loaded != null && loaded.steps != null && loaded.steps.Count > 0)
        {
            steps = loaded.steps;
            currentStep = steps[0];

            Debug.Log(
                "[MissionReplayController] Misión cargada correctamente: " +
                missionFileName +
                " | Pasos: " + steps.Count
            );
        }
        else
        {
            steps = new List<MissionStep>();
            currentStep = null;
            Debug.LogError("[MissionReplayController] No se pudo parsear el archivo JSON de misión o no tiene pasos.");
        }
    }

    private void AdvanceStep()
    {
        currentIndex++;

        if (currentIndex >= steps.Count)
        {
            if (loopReplay)
            {
                RestartCurrentDemo();
                return;
            }

            currentIndex = steps.Count - 1;
            return;
        }

        currentStep = steps[currentIndex];

        startPosition = robot.position;
        targetPosition = GridToWorld(currentStep.x, currentStep.y);

        startRotation = robot.rotation;
        targetRotation = CalculateTargetRotation(
            startPosition,
            targetPosition,
            startRotation
        );

        timer = 0f;

        ApplyRobotVisualState(currentStep);
        AddTrailPoint(targetPosition);
        CheckVictimFound(currentStep);
    }

    private Quaternion CalculateTargetRotation(
        Vector3 fromPosition,
        Vector3 toPosition,
        Quaternion fallbackRotation
    )
    {
        Vector3 direction = toPosition - fromPosition;
        direction.y = 0f;

        if (direction.sqrMagnitude < 0.001f)
        {
            return fallbackRotation;
        }

        return Quaternion.LookRotation(direction.normalized, Vector3.up);
    }

    private void CheckVictimFound(MissionStep step)
    {
        if (!step.victim_found)
        {
            return;
        }

        victimAlreadyMarked = true;
        lastVictimLocation = new Vector2Int(step.victim_x, step.victim_y);

        CreateVictimFoundMarker(step.victim_x, step.victim_y);

        Debug.Log("[MissionReplayController] Víctima encontrada en: (" + step.victim_x + ", " + step.victim_y + ")");
    }

    private void CreateVictimFoundMarker(int x, int y)
    {
        ClearVictimFoundMarker();

        if (victimFoundMarkerPrefab != null)
        {
            victimFoundMarker = Instantiate(victimFoundMarkerPrefab);
        }
        else
        {
            victimFoundMarker = GameObject.CreatePrimitive(PrimitiveType.Cylinder);
        }

        victimFoundMarker.name = "Victim Found Marker";
        victimFoundMarker.transform.position = GridToWorld(x, y, 1.1f);
        victimFoundMarker.transform.localScale = new Vector3(0.65f, 0.08f, 0.65f);

        Renderer markerRenderer = victimFoundMarker.GetComponent<Renderer>();

        if (markerRenderer != null)
        {
            markerRenderer.material.color = Color.magenta;
        }
    }

    private void ClearVictimFoundMarker()
    {
        if (victimFoundMarker != null)
        {
            Destroy(victimFoundMarker);
            victimFoundMarker = null;
        }
    }

    private Vector3 GridToWorld(int x, int y)
    {
        return GridToWorld(x, y, robotHeight);
    }

    private Vector3 GridToWorld(int x, int y, float height)
    {
        float worldX = (x - mapWidth / 2f) * cellSize;
        float worldZ = (y - mapHeight / 2f) * cellSize;

        return new Vector3(worldX, height, worldZ);
    }

    private void SetupBaseMarker()
    {
        if (baseMarker == null)
        {
            return;
        }

        baseMarker.position = GridToWorld(10, 10, 0.12f);
        baseMarker.localScale = new Vector3(1.8f, 0.18f, 1.8f);

        Renderer markerRenderer = baseMarker.GetComponent<Renderer>();

        if (markerRenderer != null)
        {
            markerRenderer.material.color = Color.blue;
        }
    }

    private void SetupTrail()
    {
        if (trailLine == null)
        {
            GameObject trailObject = new GameObject("Mission Trail");
            trailLine = trailObject.AddComponent<LineRenderer>();
            trailLine.widthMultiplier = 0.18f;
            trailLine.positionCount = 0;
            trailLine.useWorldSpace = true;

            Material material = new Material(Shader.Find("Sprites/Default"));
            material.color = Color.cyan;
            trailLine.material = material;
        }
    }

    private void AddTrailPoint(Vector3 position)
    {
        if (trailLine == null)
        {
            return;
        }

        Vector3 trailPosition = new Vector3(position.x, 0.12f, position.z);

        trailLine.positionCount += 1;
        trailLine.SetPosition(trailLine.positionCount - 1, trailPosition);
    }

    private void ClearTrail()
    {
        if (trailLine != null)
        {
            trailLine.positionCount = 0;
        }
    }

    private void ApplyRobotVisualState(MissionStep step)
    {
        if (robot == null)
        {
            return;
        }

        Color targetColor;

        if (step.victim_found)
        {
            targetColor = Color.magenta;
        }
        else if (step.return_to_base_mode)
        {
            targetColor = Color.blue;
        }
        else if (step.victim_search_mode)
        {
            targetColor = new Color(0.8f, 0.2f, 1f);
        }
        else if (step.risk_level == "ALTO")
        {
            targetColor = Color.red;
        }
        else if (step.risk_level == "MEDIO")
        {
            targetColor = Color.yellow;
        }
        else
        {
            targetColor = Color.green;
        }

        RescueRobotVisualStable stableVisual = robot.GetComponentInChildren<RescueRobotVisualStable>();

        if (stableVisual == null)
        {
            stableVisual = FindAnyObjectByType<RescueRobotVisualStable>();
        }

        if (stableVisual != null)
        {
            stableVisual.SetStatusColor(targetColor);
            return;
        }

        QuadrupedRobotVisual quadrupedVisual = robot.GetComponent<QuadrupedRobotVisual>();

        if (quadrupedVisual != null)
        {
            quadrupedVisual.SetRobotColor(targetColor);
            return;
        }

        Renderer[] renderers = robot.GetComponentsInChildren<Renderer>();

        foreach (Renderer robotRenderer in renderers)
        {
            robotRenderer.material.color = targetColor;
        }
    }

    private void SetupHudStyles()
    {
        hudStyle = new GUIStyle();
        hudStyle.fontSize = 32;
        hudStyle.fontStyle = FontStyle.Bold;
        hudStyle.normal.textColor = Color.white;

        titleStyle = new GUIStyle();
        titleStyle.fontSize = 40;
        titleStyle.fontStyle = FontStyle.Bold;
        titleStyle.normal.textColor = Color.white;

        modeStyle = new GUIStyle();
        modeStyle.fontSize = 32;
        modeStyle.fontStyle = FontStyle.Bold;
        modeStyle.normal.textColor = Color.cyan;

        helpStyle = new GUIStyle();
        helpStyle.fontSize = 26;
        helpStyle.fontStyle = FontStyle.Bold;
        helpStyle.normal.textColor = Color.white;

        victimStyle = new GUIStyle();
        victimStyle.fontSize = 32;
        victimStyle.fontStyle = FontStyle.Bold;
        victimStyle.normal.textColor = Color.magenta;
    }

    void OnGUI()
    {
        if (currentStep == null)
        {
            return;
        }

        float panelX = 25f;
        float panelY = 25f;
        float panelW = 910f;
        float panelH = 560f;

        GUI.Box(new Rect(panelX, panelY, panelW, panelH), "");

        float x = panelX + 30f;
        float y = panelY + 20f;

        GUI.Label(
            new Rect(x, y, 790f, 50f),
            "RescueTwin AI - Demo Unity",
            titleStyle
        );

        y += 65f;

        if (useDemoSelector)
        {
            GUI.Label(
                new Rect(x, y, 790f, 38f),
                "Modo carga: demos predefinidas",
                hudStyle
            );

            y += 42f;

            GUI.Label(
                new Rect(x, y, 790f, 38f),
                "Demo actual: " + currentDemo + " / " + maxDemo,
                hudStyle
            );
        }
        else
        {
            GUI.Label(
                new Rect(x, y, 790f, 38f),
                "Modo carga: misión manual",
                hudStyle
            );

            y += 42f;

            GUI.Label(
                new Rect(x, y, 790f, 38f),
                "Archivo manual: " + missionFileName,
                hudStyle
            );
        }

        y += 42f;

        GUI.Label(
            new Rect(x, y, 790f, 38f),
            "Archivo: " + missionFileName,
            hudStyle
        );

        y += 42f;

        GUI.Label(
            new Rect(x, y, 790f, 38f),
            "Step: " + currentStep.step,
            hudStyle
        );

        y += 42f;

        GUI.Label(
            new Rect(x, y, 790f, 38f),
            "Posición: (" + currentStep.x + ", " + currentStep.y + ")",
            hudStyle
        );

        y += 42f;

        GUI.Label(
            new Rect(x, y, 790f, 38f),
            "Acción: " + currentStep.action,
            hudStyle
        );

        y += 42f;

        GUI.Label(
            new Rect(x, y, 790f, 38f),
            "Riesgo: " + currentStep.risk_level,
            hudStyle
        );

        y += 42f;

        GUI.Label(
            new Rect(x, y, 790f, 38f),
            "Batería: " + currentStep.battery_level,
            hudStyle
        );

        y += 42f;

        string mode = "EXPLORACIÓN";

        if (currentStep.return_to_base_mode)
        {
            mode = "RETORNO A BASE";
        }
        else if (currentStep.victim_search_mode)
        {
            mode = "BÚSQUEDA DE VÍCTIMA";
        }

        GUI.Label(
            new Rect(x, y, 790f, 38f),
            "Modo: " + mode,
            modeStyle
        );

        y += 48f;

        if (victimAlreadyMarked)
        {
            GUI.Label(
                new Rect(x, y, 790f, 38f),
                "Víctima localizada en: (" + lastVictimLocation.x + ", " + lastVictimLocation.y + ")",
                victimStyle
            );
        }
        else if (currentStep.victim_detected)
        {
            GUI.Label(
                new Rect(x, y, 790f, 38f),
                "Señal de posible víctima detectada",
                victimStyle
            );
        }
        else
        {
            GUI.Label(
                new Rect(x, y, 790f, 38f),
                "Víctima: sin localización confirmada",
                hudStyle
            );
        }

        y += 42f;

        string helpText = useDemoSelector
            ? "Teclas: 1 - 9 cambiar demo | R reiniciar | V cámara POV | C foto"
            : "Teclas: R reiniciar | V cámara POV | C foto";

        GUI.Label(
            new Rect(x, y, 790f, 38f),
            helpText,
            helpStyle
        );
    }
}