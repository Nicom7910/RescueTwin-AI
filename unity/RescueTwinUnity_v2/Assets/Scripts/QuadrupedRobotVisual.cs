using UnityEngine;

public class QuadrupedRobotVisual : MonoBehaviour
{
    [Header("Body proportions")]
    public float bodyLength = 1.35f;
    public float bodyWidth = 0.58f;
    public float bodyHeight = 0.28f;

    public float bodyYOffset = 0.42f;

    [Header("Head / sensor block")]
    public float headLength = 0.34f;
    public float headWidth = 0.42f;
    public float headHeight = 0.22f;

    [Header("Leg proportions")]
    public float legUpperLength = 0.28f;
    public float legLowerLength = 0.24f;
    public float legThickness = 0.11f;
    public float footLength = 0.18f;
    public float footHeight = 0.06f;
    public float legSpreadX = 0.23f;
    public float legFrontZ = 0.40f;
    public float legBackZ = -0.40f;

    [Header("Animation")]
    public bool animateWalk = true;
    public float walkSpeed = 7.0f;
    public float legSwingAngle = 16.0f;
    public float kneeAngleBase = 18.0f;
    public float bodyBounce = 0.018f;

    [Header("Visual orientation")]
    public float visualYawOffset = 0f;

    [Header("Materials optional")]
    public Material bodyMaterial;
    public Material legMaterial;
    public Material sensorMaterial;

    private Transform visualRoot;

    private Transform frontLeftUpper;
    private Transform frontRightUpper;
    private Transform backLeftUpper;
    private Transform backRightUpper;

    private Transform frontLeftLower;
    private Transform frontRightLower;
    private Transform backLeftLower;
    private Transform backRightLower;

    private float animationTime = 0f;

    private void Start()
    {
        BuildRobot();
    }

    private void Update()
    {
        if (animateWalk)
        {
            AnimateLegs();
        }
    }

    public void SetRobotColor(Color color)
    {
        if (visualRoot == null)
        {
            return;
        }

        Renderer[] renderers = visualRoot.GetComponentsInChildren<Renderer>();

        foreach (Renderer renderer in renderers)
        {
            if (renderer.gameObject.name.Contains("SensorLens"))
            {
                continue;
            }

            if (renderer.gameObject.name.Contains("SensorSide"))
            {
                continue;
            }

            renderer.material.color = color;
        }
    }

    private void BuildRobot()
    {
        ClearPreviousVisual();

        GameObject root = new GameObject("QuadrupedVisualRoot");
        root.transform.SetParent(transform, false);
        root.transform.localPosition = Vector3.zero;
        root.transform.localRotation = Quaternion.Euler(0f, visualYawOffset, 0f);
        visualRoot = root.transform;

        GameObject body = CreateCube(
            "Body",
            new Vector3(0f, bodyYOffset, 0f),
            new Vector3(bodyWidth, bodyHeight, bodyLength),
            bodyMaterial,
            new Color(0.22f, 0.25f, 0.28f)
        );
        body.transform.SetParent(visualRoot, false);

        GameObject topCover = CreateCube(
            "TopCover",
            new Vector3(0f, bodyYOffset + 0.10f, -0.02f),
            new Vector3(bodyWidth * 0.82f, bodyHeight * 0.35f, bodyLength * 0.60f),
            bodyMaterial,
            new Color(0.17f, 0.20f, 0.22f)
        );
        topCover.transform.SetParent(visualRoot, false);

        GameObject rearPack = CreateCube(
            "RearPack",
            new Vector3(0f, bodyYOffset + 0.03f, -bodyLength * 0.34f),
            new Vector3(bodyWidth * 0.62f, bodyHeight * 0.45f, bodyLength * 0.18f),
            bodyMaterial,
            new Color(0.14f, 0.16f, 0.18f)
        );
        rearPack.transform.SetParent(visualRoot, false);

        GameObject neck = CreateCube(
            "Neck",
            new Vector3(0f, bodyYOffset + 0.02f, bodyLength * 0.42f),
            new Vector3(bodyWidth * 0.42f, bodyHeight * 0.45f, 0.14f),
            bodyMaterial,
            new Color(0.18f, 0.20f, 0.22f)
        );
        neck.transform.SetParent(visualRoot, false);

        GameObject head = CreateCube(
            "Head",
            new Vector3(0f, bodyYOffset + 0.04f, bodyLength * 0.58f),
            new Vector3(headWidth, headHeight, headLength),
            bodyMaterial,
            new Color(0.16f, 0.18f, 0.20f)
        );
        head.transform.SetParent(visualRoot, false);

        GameObject sensorHousing = CreateCube(
            "SensorHousing",
            new Vector3(0f, bodyYOffset + 0.07f, bodyLength * 0.70f),
            new Vector3(headWidth * 0.55f, headHeight * 0.35f, 0.10f),
            sensorMaterial,
            new Color(0.25f, 0.30f, 0.34f)
        );
        sensorHousing.transform.SetParent(visualRoot, false);

        GameObject sensorLens = CreateSphere(
            "SensorLens",
            new Vector3(0f, bodyYOffset + 0.05f, bodyLength * 0.78f),
            new Vector3(0.12f, 0.12f, 0.12f),
            sensorMaterial,
            new Color(0.35f, 0.85f, 1.0f)
        );
        sensorLens.transform.SetParent(visualRoot, false);

        GameObject leftSensor = CreateSphere(
            "SensorSideLeft",
            new Vector3(-0.09f, bodyYOffset + 0.03f, bodyLength * 0.74f),
            new Vector3(0.06f, 0.06f, 0.06f),
            sensorMaterial,
            new Color(0.35f, 0.85f, 1.0f)
        );
        leftSensor.transform.SetParent(visualRoot, false);

        GameObject rightSensor = CreateSphere(
            "SensorSideRight",
            new Vector3(0.09f, bodyYOffset + 0.03f, bodyLength * 0.74f),
            new Vector3(0.06f, 0.06f, 0.06f),
            sensorMaterial,
            new Color(0.35f, 0.85f, 1.0f)
        );
        rightSensor.transform.SetParent(visualRoot, false);

        GameObject antennaBase = CreateCylinder(
            "AntennaBase",
            new Vector3(0f, bodyYOffset + 0.16f, 0.08f),
            new Vector3(0.04f, 0.03f, 0.04f),
            sensorMaterial,
            new Color(0.22f, 0.25f, 0.28f)
        );
        antennaBase.transform.SetParent(visualRoot, false);

        GameObject antenna = CreateCylinder(
            "Antenna",
            new Vector3(0f, bodyYOffset + 0.27f, 0.08f),
            new Vector3(0.02f, 0.09f, 0.02f),
            sensorMaterial,
            new Color(0.35f, 0.85f, 1.0f)
        );
        antenna.transform.SetParent(visualRoot, false);

        frontLeftUpper = CreateLeg(
            "FrontLeft",
            new Vector3(-legSpreadX, bodyYOffset - 0.05f, legFrontZ),
            true
        );

        frontRightUpper = CreateLeg(
            "FrontRight",
            new Vector3(legSpreadX, bodyYOffset - 0.05f, legFrontZ),
            true
        );

        backLeftUpper = CreateLeg(
            "BackLeft",
            new Vector3(-legSpreadX, bodyYOffset - 0.05f, legBackZ),
            false
        );

        backRightUpper = CreateLeg(
            "BackRight",
            new Vector3(legSpreadX, bodyYOffset - 0.05f, legBackZ),
            false
        );
    }

    private Transform CreateLeg(string namePrefix, Vector3 hipPosition, bool frontLeg)
    {
        GameObject upperPivot = new GameObject(namePrefix + "_UpperPivot");
        upperPivot.transform.SetParent(visualRoot, false);
        upperPivot.transform.localPosition = hipPosition;

        GameObject upperLeg = CreateCube(
            namePrefix + "_UpperLeg",
            new Vector3(0f, -legUpperLength / 2f, 0f),
            new Vector3(legThickness, legUpperLength, legThickness),
            legMaterial,
            new Color(0.10f, 0.10f, 0.10f)
        );
        upperLeg.transform.SetParent(upperPivot.transform, false);

        GameObject lowerPivot = new GameObject(namePrefix + "_LowerPivot");
        lowerPivot.transform.SetParent(upperPivot.transform, false);
        lowerPivot.transform.localPosition = new Vector3(0f, -legUpperLength, 0f);

        GameObject lowerLeg = CreateCube(
            namePrefix + "_LowerLeg",
            new Vector3(0f, -legLowerLength / 2f, 0f),
            new Vector3(legThickness * 0.88f, legLowerLength, legThickness * 0.88f),
            legMaterial,
            new Color(0.08f, 0.08f, 0.08f)
        );
        lowerLeg.transform.SetParent(lowerPivot.transform, false);

        GameObject foot = CreateCube(
            namePrefix + "_Foot",
            new Vector3(0f, -legLowerLength - footHeight / 2f, frontLeg ? 0.03f : -0.03f),
            new Vector3(legThickness * 1.35f, footHeight, footLength),
            legMaterial,
            new Color(0.05f, 0.05f, 0.05f)
        );
        foot.transform.SetParent(lowerPivot.transform, false);

        if (namePrefix == "FrontLeft")
        {
            frontLeftLower = lowerPivot.transform;
        }
        else if (namePrefix == "FrontRight")
        {
            frontRightLower = lowerPivot.transform;
        }
        else if (namePrefix == "BackLeft")
        {
            backLeftLower = lowerPivot.transform;
        }
        else if (namePrefix == "BackRight")
        {
            backRightLower = lowerPivot.transform;
        }

        return upperPivot.transform;
    }

    private void AnimateLegs()
    {
        if (visualRoot == null)
        {
            return;
        }

        animationTime += Time.deltaTime * walkSpeed;

        float swingA = Mathf.Sin(animationTime) * legSwingAngle;
        float swingB = Mathf.Sin(animationTime + Mathf.PI) * legSwingAngle;

        float kneeA = kneeAngleBase + Mathf.Abs(Mathf.Sin(animationTime)) * 14f;
        float kneeB = kneeAngleBase + Mathf.Abs(Mathf.Sin(animationTime + Mathf.PI)) * 14f;

        if (frontLeftUpper != null)
        {
            frontLeftUpper.localRotation = Quaternion.Euler(swingA, 0f, 0f);
        }

        if (backRightUpper != null)
        {
            backRightUpper.localRotation = Quaternion.Euler(swingA, 0f, 0f);
        }

        if (frontRightUpper != null)
        {
            frontRightUpper.localRotation = Quaternion.Euler(swingB, 0f, 0f);
        }

        if (backLeftUpper != null)
        {
            backLeftUpper.localRotation = Quaternion.Euler(swingB, 0f, 0f);
        }

        if (frontLeftLower != null)
        {
            frontLeftLower.localRotation = Quaternion.Euler(kneeA, 0f, 0f);
        }

        if (backRightLower != null)
        {
            backRightLower.localRotation = Quaternion.Euler(kneeA, 0f, 0f);
        }

        if (frontRightLower != null)
        {
            frontRightLower.localRotation = Quaternion.Euler(kneeB, 0f, 0f);
        }

        if (backLeftLower != null)
        {
            backLeftLower.localRotation = Quaternion.Euler(kneeB, 0f, 0f);
        }

        visualRoot.localPosition = new Vector3(
            0f,
            Mathf.Abs(Mathf.Sin(animationTime * 2f)) * bodyBounce,
            0f
        );
    }

    private GameObject CreateCube(
        string objectName,
        Vector3 localPosition,
        Vector3 localScale,
        Material material,
        Color fallbackColor
    )
    {
        GameObject obj = GameObject.CreatePrimitive(PrimitiveType.Cube);
        obj.name = objectName;
        obj.transform.localPosition = localPosition;
        obj.transform.localScale = localScale;

        Renderer renderer = obj.GetComponent<Renderer>();

        if (renderer != null)
        {
            if (material != null)
            {
                renderer.material = material;
            }
            else
            {
                renderer.material.color = fallbackColor;
            }

            renderer.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.On;
            renderer.receiveShadows = true;
        }

        return obj;
    }

    private GameObject CreateSphere(
        string objectName,
        Vector3 localPosition,
        Vector3 localScale,
        Material material,
        Color fallbackColor
    )
    {
        GameObject obj = GameObject.CreatePrimitive(PrimitiveType.Sphere);
        obj.name = objectName;
        obj.transform.localPosition = localPosition;
        obj.transform.localScale = localScale;

        Renderer renderer = obj.GetComponent<Renderer>();

        if (renderer != null)
        {
            if (material != null)
            {
                renderer.material = material;
            }
            else
            {
                renderer.material.color = fallbackColor;
            }

            renderer.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.On;
            renderer.receiveShadows = true;
        }

        return obj;
    }

    private GameObject CreateCylinder(
        string objectName,
        Vector3 localPosition,
        Vector3 localScale,
        Material material,
        Color fallbackColor
    )
    {
        GameObject obj = GameObject.CreatePrimitive(PrimitiveType.Cylinder);
        obj.name = objectName;
        obj.transform.localPosition = localPosition;
        obj.transform.localScale = localScale;

        Renderer renderer = obj.GetComponent<Renderer>();

        if (renderer != null)
        {
            if (material != null)
            {
                renderer.material = material;
            }
            else
            {
                renderer.material.color = fallbackColor;
            }

            renderer.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.On;
            renderer.receiveShadows = true;
        }

        return obj;
    }

    private void ClearPreviousVisual()
    {
        for (int i = transform.childCount - 1; i >= 0; i--)
        {
            if (Application.isPlaying)
            {
                Destroy(transform.GetChild(i).gameObject);
            }
            else
            {
                DestroyImmediate(transform.GetChild(i).gameObject);
            }
        }
    }
}