from raytracing.graphicComponents import *
import numpy as np
import sys


class Graphic:
    """ The base class that defines the graphic of any element.

    A Graphic can be a composition of different graphic components (ex.: A lens graphic is two arrows).

    Args:
        *components: The required graphic components that define the Graphic.

            These graphic components should be instantiated at x = 0 to allow for proper positioning and scaling.

    """

    def __init__(self, components=None, label: str = None,
                 x=0.0, y=0.0, fixedWidth=False):
        self._components = components
        self.label = None
        self.points = []

        self.x = x
        self.y = y
        self.useAutoScale = not fixedWidth

        if label is not None:
            self.label = Label(text=label, x=self.centroid[0], y=self.halfHeight * 1.2)

    @property
    def hasLabel(self):
        if self.label is None:
            return False
        return True

    @property
    def components(self):
        """ Can be overwritten by other graphics """
        return self._components

    @property
    def halfHeight(self) -> float:
        """ Maximum absolute Y-value of the graphic (not affected by the transforms).
        Used internally to auto-scale. """
        halfHeight = 0
        for component in self.components:
            componentMaxY = np.max(np.abs(component.xy), axis=0)[1]
            if componentMaxY > halfHeight:
                halfHeight = componentMaxY
        return halfHeight

    @property
    def centroid(self):
        xy = []
        for component in self.components:
            xy.extend(component.xy)
        return np.mean(xy, axis=0)

    @property
    def patches2D(self):
        return [c.patch for c in self.components]

    @property
    def length(self):
        return np.sum([c.length for c in self.components])


class GraphicOf:
    def __new__(cls, element, x=0.0) -> Union[Graphic, None]:
        instance = type(element).__name__
        if instance is 'Lens':
            return LensGraphic(element, x=x)
        if instance is 'Space':
            return None
        if instance is 'Aperture':
            return ApertureGraphic(element, x=x)
        if element.surfaces:
            return SurfacesGraphic(element, x=x)
        else:
            return MatrixGraphic(element, x=x)


class MatrixGraphic(Graphic):
    def __init__(self, matrix, x=0.0, fixedWidth=False):
        self.matrix = matrix
        super(MatrixGraphic, self).__init__(x=x, fixedWidth=fixedWidth, label=self.matrix.label)

    @property
    def components(self):
        if self._components is None:
            self._components = self.mainComponents
            self._components.extend(self.apertureComponents)

            # self.drawLabels(z=0, axes=axes)
            # self.drawCardinalPoints(z=0, axes=axes)
            # if self.matrix.L != 0:
            #     self.drawVertices(z=0, axes=axes)
            # self.drawPointsOfInterest(z=0, axes=axes)
            # self.drawPrincipalPlanes(z=0, axes=axes)
        return self._components

    @property
    def mainComponents(self):
        return []

    @property
    def apertureComponents(self):
        # todo: make Aperture a single component with +- y
        if self.matrix.apertureDiameter != float('+Inf'):
            halfHeight = self.matrix.apertureDiameter / 2.0
            return [Aperture(y=halfHeight, width=self.matrix.L),
                    Aperture(y=-halfHeight, width=self.matrix.L)]

    @property
    def cardinalPoints(self) -> List[Point]:
        points = []
        for f in self.matrix.focusPositions(self.x):
            if f is not None:
                points.append(Point(x=f))
        return points

    @property
    def verticesPoints(self) -> List[Point]:
        return [Point(self.x + self.matrix.frontVertex, text='$V_f$', color='0.5'),
                Point(self.x + self.matrix.backVertex, text='$V_b$', color='0.5')]

    def display(self):
        """ Display this component, without any ray tracing but with
        all of its cardinal points and planes.

        Examples
        --------
        >>> from raytracing import *
        >>> # Mat is an ABCD matrix of an object
        >>> Mat= Matrix(A=1,B=0,C=-1/5,D=1,physicalLength=2,frontVertex=-1,backVertex=2,
        >>>            frontIndex=1.5,backIndex=1,label='Lens')
        >>> Mat.display()

        And the result is shown in the following figure:

        .. image:: display.png
            :width: 70%
            :align: center


        Notes
        -----
        If the component has no power (i.e. C == 0) this will fail.
        """
        # todo: handle points outside components ?
        self.points = []
        self.points.extend(self.cardinalPoints)
        if self.matrix.L != 0:
            self.points.extend(self.verticesPoints)

        from .figureManager import MplFigure
        from .imagingpath import ImagingPath
        path = ImagingPath(elements=[self.matrix])
        figure = MplFigure(path)
        figure.graphics = [self]
        figure.create(title="Element properties")
        figure.display2D()


class LensGraphic(MatrixGraphic):

    @property
    def mainComponents(self):
        return [DoubleThinArrow(self.matrix.displayHalfHeight()*2)]


class ApertureGraphic(MatrixGraphic):
    def __init__(self, matrix, x=0.0):
        super().__init__(matrix, x=x, fixedWidth=True)


class SurfacesGraphic(MatrixGraphic):
    def __init__(self, matrix, x=0.0):
        super().__init__(matrix, x=x, fixedWidth=True)
    @property
    def components(self):
        if self._components is None:
            self._components = self.mainComponents
        return self._components

    @property
    def mainComponents(self):
        components = []
        halfHeight = self.matrix.displayHalfHeight()

        z = 0
        for i, surfaceA in enumerate(self.matrix.surfaces[:-1]):
            surfaceB = self.matrix.surfaces[i+1]
            p = SurfacePair(surfaceA, surfaceB, x=z, halfHeight=halfHeight)
            z += surfaceA.L
            components.append(p)

            # todo: might be required to get correct width depending on surface curvatures
            outerWidth = p.corners[1] - p.corners[0]
            components.append(Aperture(y=halfHeight, x=p.corners[0], width=outerWidth))
            components.append(Aperture(y=-halfHeight, x=p.corners[0], width=outerWidth))

        return components
