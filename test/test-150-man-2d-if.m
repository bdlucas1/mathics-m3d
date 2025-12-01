Manipulate[
    Plot[
        If[x > threshold, x, -x],
        {x,-1,1}
    ],
    {{threshold,0},-1,1,0.05}
]
